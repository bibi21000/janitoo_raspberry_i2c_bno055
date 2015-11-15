# -*- coding: utf-8 -*-
"""The Raspberry http thread

Server files using the http protocol

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

import logging
logger = logging.getLogger("janitoo.raspberry")
import os, sys
import threading

from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.component import JNTComponent
from janitoo.bus import JNTBus
import RPi.GPIO as GPIO

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_WEB_CONTROLLER = 0x1030
COMMAND_WEB_RESOURCE = 0x1031
COMMAND_DOC_RESOURCE = 0x1032

assert(COMMAND_DESC[COMMAND_WEB_CONTROLLER] == 'COMMAND_WEB_CONTROLLER')
assert(COMMAND_DESC[COMMAND_WEB_RESOURCE] == 'COMMAND_WEB_RESOURCE')
assert(COMMAND_DESC[COMMAND_DOC_RESOURCE] == 'COMMAND_DOC_RESOURCE')
##############################################################

def make_http_resource(**kwargs):
    return HttpResourceComponent(**kwargs)

class GpioBus(JNTBus):
    """A bus to manage GPIO
    """
    def __init__(self, **kwargs):
        """
        :param kwargs: parameters transmitted to :py:class:`smbus.SMBus` initializer
        """
        JNTBus.__init__(self, **kwargs)
        self._lock =  threading.Lock()

        uuid="boardmode"
        self.values[uuid] = self.value_factory['config_list'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The board mode to use',
            label='Boardmode',
            default='BOARD',
            self.list_items=['BCM', 'BOARD'],
        )

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        #~ print "it's me %s : %s" % (self.values['upsname'].data, self._ups_stats_last)
        if GPIO.RPI_INFO['P1_REVISION']>0:
            return True
        return False

    def start(self, mqttc, trigger_thread_reload_cb=None):
        """Start the bus
        """
        JNTBus.start(self, mqttc, trigger_thread_reload_cb)
        if self.values["boardmode"].data == "BCM":
            GPIO.setmode(GPIO.BCM)
        else:
            GPIO.setmode(GPIO.BOARD)

    def stop(self):
        """Stop the bus
        """
        GPIO.cleanup()
        JNTBus.stop(self)

class GpioComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, path='generic', bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'pigpio.resource')
        name = kwargs.pop('name', "HTTP resource")
        product_name = kwargs.pop('product_name', "HTTP resource")
        product_type = kwargs.pop('product_type', "Software")
        product_manufacturer = kwargs.pop('product_manufacturer', "Janitoo")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                product_name=product_name, product_type=product_type, product_manufacturer="Janitoo", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        self.path = path
        dirname='.'
        if 'home_dir' in self.options.data and self.options.data['home_dir'] is not None:
            dirname = self.options.data['home_dir']
        dirname = os.path.join(dirname, "public")
        dirname = os.path.join(dirname, self.path)
        self.deploy_resource(dirname)

    def start(self, mqttc):
        """Start the component.

        """
        JNTComponent.start(self, mqttc)
        return True

    def stop(self):
        """Stop the component.

        """
        JNTComponent.stop(self)
        return True

    def deploy_resource(self, destination):
        """
        """
        pass

    def check_heartbeat_file(self, filename):
        """Check that the component is 'available'

        """
        dirname='.'
        if 'home_dir' in self.options.data and self.options.data['home_dir'] is not None:
            dirname = self.options.data['home_dir']
        dirname = os.path.join(dirname, "public", filename)
        return os.path.exists(dirname)

class BasicResourceComponent(HttpResourceComponent):
    """ A resource ie /rrd """

    def __init__(self, path='generic', bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'http.basic')
        product_name = kwargs.pop('product_name', "HTTP basic resource")
        name = kwargs.pop('name', "Http basic resource")
        HttpResourceComponent.__init__(self, path, oid=oid, bus=bus, addr=addr, name=name,
                product_name=product_name, **kwargs)
        uuid="resource"
        self.values[uuid] = self.value_factory['sensor_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The http resource: host:port',
            label='Resource',
            get_data_cb=self.get_resource,
            genre=0x01,
            cmd_class=COMMAND_WEB_RESOURCE,
        )
        #~ config_value = self.values[uuid].create_config_value(help='The resource path', label='resource', type=0x08)
        #~ self.values[config_value.uuid] = config_value
        poll_value = self.values[uuid].create_poll_value(default=1800)
        self.values[poll_value.uuid] = poll_value

    def get_resource(self, node_uuid, index):
        """
        """
        #~ print self._bus.get_resource_path() % self.path
        return self._bus.get_resource_path() % '%s/' % self.path

    def deploy_resource(self, destination):
        """
        """
        for subdir in DEPLOY_DIRS:
            try:
                source = os.path.join(self.resource_filename('public'), self.path, subdir)
                logger.debug('[%s] - public source = %s', self.__class__.__name__, source)
                if os.path.isdir(source):
                    if not os.path.exists(os.path.join(destination,subdir)):
                        os.makedirs(os.path.join(destination,subdir))
                    copy_tree(source, os.path.join(destination,subdir), preserve_mode=1, preserve_times=1, preserve_symlinks=0, update=0, verbose=0, dry_run=0)
            except:
                logger.exception('[%s] - Exception in deploy_resource', self.__class__.__name__)
        try:
            source = os.path.join(self.resource_filename('public'), "html")
            logger.debug('[%s] - public html source = %s', self.__class__.__name__, source)
            if os.path.isdir(source):
                src_files = os.listdir(source)
                for file_name in src_files:
                    try:
                        full_file_name = os.path.join(source, file_name)
                        if (os.path.isfile(full_file_name)):
                            shutil.copy(full_file_name, destination)
                    except:
                        logger.exception('[%s] - Exception in deploy_resource', self.__class__.__name__)
        except:
            logger.exception('[%s] - Exception in deploy_resource', self.__class__.__name__)


class DocumentationResourceComponent(HttpResourceComponent):
    """ A resource ie /rrd """

    def __init__(self, path='generic', bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'http.doc')
        product_name = kwargs.pop('product_name', "HTTP documentation resource")
        name = kwargs.pop('name', "Http documentation resource")
        HttpResourceComponent.__init__(self, path=os.path.join('doc',path), oid=oid, bus=bus, addr=addr, name=name,
                product_name=product_name, **kwargs)
        uuid="key"
        self.values[uuid] = self.value_factory['sensor_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The key of documentation (ie controller.audiovideo.installation, node.audiovideo.samsung_ue46, ...))',
            label='Key doc.',
            get_data_cb=self.get_key,
            is_readonly=True,
            genre=0x01,
            cmd_class=COMMAND_DOC_RESOURCE,
        )
        self.configs_instances = self.values[uuid].instances
        #~ print self.configs_instances
        poll_value = self.values[uuid].create_poll_value(default=1800)
        self.values[poll_value.uuid] = poll_value
        uuid="resource"
        self.values[uuid] = self.value_factory['sensor_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The http documentation : host:port/path',
            label='Documentation',
            get_data_cb=self.get_resource,
            genre=0x01,
            cmd_class=COMMAND_WEB_RESOURCE,
        )
        config_value = self.values[uuid].create_config_value(help='The resource path', label='resource', type=0x08)
        self.values[config_value.uuid] = config_value
        self.values[config_value.uuid].instances = self.configs_instances
        poll_value = self.values[uuid].create_poll_value(default=1800)
        self.values[poll_value.uuid] = poll_value

    def deploy_resource(self, destination):
        """
        """
        try:
            source = self.resource_filename('docs')
            logger.debug('[%s] - doc source = %s', self.__class__.__name__, source)
            if os.path.isdir(source):
                #~ if os.path.isfile(source):
                copy_tree(source, destination, preserve_mode=1, preserve_times=1, preserve_symlinks=0, update=0, verbose=0, dry_run=0)
        except:
            logger.exception('[%s] - Exception in deploy_resource', self.__class__.__name__)

    def get_key(self, node_uuid, index):
        """
        """
        pass

    def get_resource(self, node_uuid, index):
        """
        """
        #~ print self._bus.get_resource_path() % self.path
        pass

