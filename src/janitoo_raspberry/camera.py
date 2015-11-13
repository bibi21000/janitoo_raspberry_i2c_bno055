# -*- coding: utf-8 -*-
"""The Raspberry camera worker

Installation :

.. code-block:: bash

    sudo apt-get install python-pycamera

"""

__license__ = """
    This file is part of Janitoo.

    Janitoo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Janitoo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Janitoo. If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger( 'janitoo.raspberry' )
import os, sys
import threading
import time
import datetime
import socket
from janitoo.thread import JNTBusThread
from janitoo.bus import JNTBus
from janitoo.component import JNTComponent
from janitoo.thread import BaseThread
from janitoo.options import get_option_autostart
from janitoo.threads.http import HttpResourceComponent
import picamera

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_CONTROLLER = 0x1050

assert(COMMAND_DESC[COMMAND_CONTROLLER] == 'COMMAND_CONTROLLER')
##############################################################

def make_photo(**kwargs):
    return CameraPhoto(**kwargs)

def make_video(**kwargs):
    return CameraVideo(**kwargs)

def make_stream(**kwargs):
    return CameraStream(**kwargs)

def make_http_resource(**kwargs):
    return CameraResource(**kwargs)

CAMERA_DIR = ['photo/snapshot', 'photo/sequence']

class CameraBus(JNTBus):
    """A pseudo-bus to handle the Raspberry Camera
    """
    def __init__(self, **kwargs):
        """
        :param int bus_id: the SMBus id (see Raspberry Pi documentation)
        :param kwargs: parameters transmitted to :py:class:`smbus.SMBus` initializer
        """
        JNTBus.__init__(self, **kwargs)
        self._lock = threading.Lock()
        self.camera = None
        directory = self.get_public_directory()
        for didir in CAMERA_DIR:
            ndir = os.path.join(directory,didir)
            if not os.path.exists(ndir):
                os.makedirs(ndir)
        uuid="led"
        self.values[uuid] = self.value_factory['config_boolean'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Led state',
            label='led',
            default=True,
        )

    def get_public_directory(self):
        """"
        """
        dirname='.'
        if 'home_dir' in self.options.data and self.options.data['home_dir'] is not None:
            dirname = self.options.data['home_dir']
        dirname = os.path.join(dirname, "public")
        directory = os.path.join(dirname, "picamera")
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        #~ print "it's me %s : %s" % (self.values['upsname'].data, self._ups_stats_last)
        if self.camera is not None:
            return self.camera.closed
        return False

    def start(self, mqttc, trigger_thread_reload_cb=None):
        """Start the bus
        """
        JNTBus.start(self, mqttc, trigger_thread_reload_cb)
        self.camera = picamera.PiCamera()

    def stop(self):
        """
        """
        JNTBus.stop(self)
        if self.camera is not None:
            self.camera.close()
            self.camera = None

    def camera_start(self):
        """Start the camera. Must be used wit camera_stop in a try finally block
        """
        locked = self._lock.acquire(False)
        if locked == True:
            if self.camera is None:
                self.camera = picamera.PiCamera()
            self.camera.led = self.values['led'].data
            self.camera.start_preview()
            # Camera warm-up time
            time.sleep(2)
        return locked

    def camera_stop(self):
        """Stop the camera. Must be used wit camera_start in a try finally block
        """
        try:
            self.camera.stop_preview()
        except:
            logger.exception("[%s] - Exception in camera_stop", self.__class__.__name__)
        try:
            self._lock.release()
        except:
            logger.exception("[%s] - Exception in camera_stop", self.__class__.__name__)

class CameraComponent(JNTComponent):
    """ Use pycamera. """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        JNTComponent.__init__(self, bus=bus, addr=addr, **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

        uuid="hflip"
        self.values[uuid] = self.value_factory['config_boolean'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Horizontal flip.',
            label='Hflip',
            default=False,
        )

        uuid="vflip"
        self.values[uuid] = self.value_factory['config_boolean'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Vertical flip.',
            label='Vflip',
            default=False,
        )

    def camera_start(self):
        """Start the camera. Must be used wit camera_stop in a try finally block
        """
        locked = self._bus.camera_start()
        if locked == True:
            self._bus.camera.hflip = self.values['hflip'].data
            self._bus.camera.vflip = self.values['vflip'].data
        return locked

    def camera_stop(self):
        """Stop the camera. Must be used wit camera_start in a try finally block
        """
        self._bus.camera_stop()

class CameraPhoto(CameraComponent):
    """ Use pycamera. """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        CameraComponent.__init__(self, 'picamera.photo', bus=bus, addr=addr, name="Photo",
                product_name="Photo", product_type="Software", product_manufacturer="Photo", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

        uuid="snpashot"
        self.values[uuid] = self.value_factory['sensor_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Take a snapshot and return the name of the video',
            label='Snapshot',
            get_data_cb=self.get_snapshot,
        )
        poll_value = self.values[uuid].create_poll_value(default=0, is_polled=False)
        self.values[poll_value.uuid] = poll_value

    def get_snapshot(self, node_uuid, index):
        """Take a snaphot
        """
        filename = None
        if self.camera_start():
            try :
                directory = os.path.join(self._bus.get_public_directory(), 'photo/snaphot')
                if not os.path.exists(directory):
                    os.makedirs(directory)
                filename = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
                filename = os.path.join(filename, '.jpg')
                self._bus.camera.capture(os.path.join(directory, filename))
            except:
                logger.exception("[%s] - Exception in get_snapshot", self.__class__.__name__)
            finally:
                self.camera_stop()
        return filename

class CameraVideo(CameraComponent):
    """ Use pycamera. """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        CameraComponent.__init__(self, 'picamera.video', bus=bus, addr=addr, name="Video",
                product_name="Video", product_type="Software", product_manufacturer="Video", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

        uuid="snpashot"
        self.values[uuid] = self.value_factory['sensor_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Take a snapshot and return the name of the photo',
            label='Snapshot',
            get_data_cb=self.get_snapshot,
        )
        config_value = self.values[uuid].create_config_value(help='The duration of the video', label='Duration', type=0x04, default = 10)
        self.values[config_value.uuid] = config_value
        poll_value = self.values[uuid].create_poll_value(default=0, is_polled=False)
        self.values[poll_value.uuid] = poll_value

    def get_snapshot(self, node_uuid, index):
        """Take a snaphot
        """
        filename = None
        if self.camera_start():
            try :
                directory = os.path.join(self._bus.get_public_directory(), 'video/snaphot')
                if not os.path.exists(directory):
                    os.makedirs(directory)
                filename = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
                self._bus.camera.start_recording(os.path.join(directory, filename, '.h264'))
                stop_timer = threading.Timer(self.values['snpashot_config'].data, self.stop_snapshot)
                stop_timer.start()
            except:
                logger.exception("[%s] - Exception in get_snapshot", self.__class__.__name__)
                self.camera_stop()
                self._bus.camera = None
        return filename

    def stop_snapshot(self):
        """Take a snaphot
        """
        self._bus.camera.stop_recording()
        self.camera_stop()

class StreamServerThread(BaseThread):
    """The stream thread


    """
    def __init__(self, section, options={}):
        """Initialise the cache thread

        Manage a cache for the rrd.

        A timer in a separated thread will pickle the cache to disk every 30 seconds.

        An other thread will update the rrd every hours

        :param options: The options used to start the worker.
        :type clientid: str
        """
        self.section = section
        BaseThread.__init__(self, options=options)
        self.config_timeout_delay = 1.5
        self.loop_sleep = 0.005
        self._host = "localhost"
        self._port = 8052
        self._server = None
        self._connection = None
        self._camera = None

    def config(self, host="localhost", port=8052, camera=None):
        """
        """
        if host is not None:
            self._host = host
        if port is not None:
            self._port = port
        if camera is not None:
            self._camera = camera

    def pre_loop(self):
        """Launch before entering the run loop. The node manager is available.
        """
        self._server = socket.socket()
        self._server.bind((self._host, self._port))
        self._server.listen(0)
        self._connection = self._server.accept()[0].makefile('wb')
        self._camera.start_recording(connection, format='h264')
        self._camera.stop_recording()

    def post_loop(self):
        """Launch after finishing the run loop. The node manager is still available.
        """
        self._camera.stop_recording()
        self._connection.close()
        self._connection = None
        self._server.close()
        self._server = None

    def loop(self):
        """Launch after finishing the run loop. The node manager is still available.
        """
        self._camera.wait_recording(self.loop_sleep)

    def run(self):
        """Run the loop
        """
        self._stopevent.clear()
        #~ self.boot()
        self.trigger_reload()
        logger.debug("[%s] - Wait for the thread reload event for initial startup", self.__class__.__name__)
        while not self._reloadevent.isSet() and not self._stopevent.isSet():
            self._reloadevent.wait(0.50)
        logger.debug("[%s] - Entering the thread loop", self.__class__.__name__)
        while not self._stopevent.isSet():
            self._reloadevent.clear()
            try:
                self.pre_loop()
            except:
                logger.exception('[%s] - Exception in pre_loop', self.__class__.__name__)
                self._stopevent.set()
            while not self._reloadevent.isSet() and not self._stopevent.isSet():
                self.loop()
            try:
                self.post_loop()
            except:
                logger.exception('[%s] - Exception in post_loop', self.__class__.__name__)

class CameraStream(CameraComponent):
    """ Use pycamera. """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        CameraComponent.__init__(self, 'picamera.stream', bus=bus, addr=addr, name="Stream",
                product_name="Stream", product_type="Software", product_manufacturer="Stream", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

        uuid="host"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The host or IP to use for the server',
            label='Host',
            default='localhost',
        )

        uuid="port"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The port',
            label='Port',
            default=8052,
        )

        uuid="actions"
        self.values[uuid] = self.value_factory['action_list'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The action on the video stream server',
            label='Actions',
            list_items=['start', 'stop'],
            set_data_cb=self.set_action,
            is_writeonly = True,
            cmd_class = COMMAND_CONTROLLER,
            genre=0x01,
        )

    def set_action(self, node_uuid, index, data):
        """Act on the server
        """
        if data == "start":
            if self.mqttc is not None:
                self.start(self.mqttc)
        elif data == "stop":
            self.stop()
        elif data == "reload":
            if self._server is not None:
                self._server.trigger_reload()

    def start(self, mqttc, trigger_thread_reload_cb=None):
        CameraComponent.start(self, mqttc, trigger_thread_reload_cb)
        self._server = StreamServerThread("stream_server", self.options.data)
        self._server.config(host=self.values["host"].data, port=self.values["port"].data, camera=self._bus.camera)
        self._server.start()

    def stop(self):
        if self._server is not None:
            self._server.stop()
            self._server = None
        CameraComponent.stop(self)

class CameraResource(HttpResourceComponent):
    """ A resource ie /camera """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        HttpResourceComponent.__init__(self, path='photo', oid='http.camera', bus=bus, addr=addr, name="Http camera resource",
                product_name="HTTP camera resource", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        dirname='.'
        if 'home_dir' in self.options.data and self.options.data['home_dir'] is not None:
            dirname = self.options.data['home_dir']
        dirname = os.path.join(dirname, "public")
        directory = os.path.join(dirname, "picamera")
        for didir in CAMERA_DIR:
            ndir = os.path.join(directory,didir)
            if not os.path.exists(ndir):
                os.makedirs(ndir)

    def get_module_dir(self):
        """
        """
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),'public')

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        return self.check_heartbeat_file("picamera")
