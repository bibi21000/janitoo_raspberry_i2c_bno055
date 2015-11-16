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

def make_input(**kwargs):
    return InputComponent(**kwargs)

def make_output(**kwargs):
    return OutputComponent(**kwargs)

def make_pwm(**kwargs):
    return PwmComponent(**kwargs)

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
            list_items=['BCM', 'BOARD'],
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

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'pigpio.generic')
        name = kwargs.pop('name', "Input")
        product_name = kwargs.pop('product_name', "GPIO")
        product_type = kwargs.pop('product_type', "Software")
        product_manufacturer = kwargs.pop('product_manufacturer', "Janitoo")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                product_name=product_name, product_type=product_type, product_manufacturer="Janitoo", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

        uuid="pin"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The pin number on the board',
            label='Pin',
            default=1,
        )

class InputComponent(GpioComponent):
    """ A resource ie /rrd """

    def __init__(self, path='generic', bus=None, addr=None, **kwargs):
        """
        """
        self._inputs = {}
        oid = kwargs.pop('oid', 'gpio.input')
        product_name = kwargs.pop('product_name', "Input GPIO")
        name = kwargs.pop('name', "Input GPIO")
        HttpResourceComponent.__init__(self, path, oid=oid, bus=bus, addr=addr, name=name,
                product_name=product_name, **kwargs)
        uuid="pullupdown"
        self.values[uuid] = self.value_factory['config_list'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Use a pull up or a pull down',
            label='Pull Up/Down',
            default='PUD_UP',
            list_items=['PUD_UP', 'PUD_DOWN'],
        )
        uuid="edge"
        self.values[uuid] = self.value_factory['config_list'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Edge to use (rising or falling)',
            label='Edge',
            default='BOTH',
            list_items=['BOTH', 'RISING', 'FALLING'],
        )
        uuid="bouncetime"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='Bouncetime should be specified in milliseconds',
            label='bouncetime',
            default=200,
        )
        uuid="trigger"
        self.values[uuid] = self.value_factory['config_boolean'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help="Should we trigger the state's change",
            label='trigger',
            default=True,
        )
        uuid="status"
        self.values[uuid] = self.value_factory['sensor_byte'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The status of the GPIO',
            label='Status',
            get_data_cb=self.get_status,
        )
        poll_value = self.values[uuid].create_poll_value(default=60)
        self.values[poll_value.uuid] = poll_value

    def get_status(self, node_uuid, index):
        """
        """
        if index in self._inputs:
            return self._inputs[index]['value']
        return None

    def trigger_status(self, channel):
        """
        """
        self.node.publish_poll(None, self.values['status'])

    def start(self, mqttc):
        """Start the component.

        """
        JNTComponent.start(self, mqttc)
        configs = len(self.values["pin"].get_index_configs())
        for config in range(configs):
            pull_up_down = GPIO.PUD_DOWN if self.values['pullupdown'].instances[config]['data'] == "PUD_DOWN" else GPIO.PUD_UP
            GPIO.setup(self.values["pin"].instances[config]['data'], GPIO.IN, pull_up_down=pull_up_down)
            sedge = self.values['edge'].instances[config]['data']
            if sedge == "RISING":
                edge = GPIO.RISING
            elif sedge == "FALLING":
                edge = GPIO.FALLING
            else:
                edge = GPIO.BOTH
            GPIO.add_event_detect(self.values["pin"].instances[config]['data'], edge, callback=self.trigger_status, bouncetime=self.values["bouncetime"].instances[config]['data'])
        return True

    def stop(self):
        """Stop the component.

        """
        configs = len(self.values["pin"].get_index_configs())
        for config in range(configs):
            GPIO.remove_event_detect(self.values["pin"].instances[config]['data'])
        JNTComponent.stop(self)
        return True

class OuputComponent(GpioComponent):
    """ A resource ie /rrd """

class PwmComponent(GpioComponent):
    """ A resource ie /rrd """
