# -*- coding: utf-8 -*-
"""The Raspberry bmp thread

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
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

import logging
logger = logging.getLogger(__name__)
import os, sys
import threading

from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.component import JNTComponent
from janitoo_raspberry_i2c.bus_i2c import I2CBus

from Adafruit_BNO055 import BNO055

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

def make_bno(**kwargs):
    return BNOComponent(**kwargs)

class BNOComponent(JNTComponent):
    """ A generic component for gpio """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'rpii2c.bno')
        name = kwargs.pop('name', "Input")
        product_name = kwargs.pop('product_name', "BMP")
        product_type = kwargs.pop('product_type', "Temperature/altitude/pressure sensor")
        product_manufacturer = kwargs.pop('product_manufacturer', "Janitoo")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                product_name=product_name, product_type=product_type, product_manufacturer="Janitoo", **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)

        uuid="addr"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The I2C address of the BNO component',
            label='Addr',
            default=0x77,
        )
        uuid="reset_pin"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The reset pin',
            label='Rst pin',
            default=None,
        )
        uuid="temperature"
        self.values[uuid] = self.value_factory['sensor_temperature'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The temperature',
            label='Temp',
            get_data_cb=self.temperature,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value

        self.sensor = None

    def temperature(self, node_uuid, index):
        self._bus.i2c_acquire()
        try:
            data = self.sensor.read_temp()
            ret = float(data)
        except:
            logger.exception('[%s] - Exception when retrieving temperature', self.__class__.__name__)
            ret = None
        finally:
            self._bus.i2c_release()
        return ret

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        return self.sensor is not None

    def start(self, mqttc):
        """Start the bus
        """
        JNTComponent.start(self, mqttc)
        self._bus.i2c_acquire()
        try:
            self.sensor = BNO055.BNO055(rst=self.values["reset_pin"].data, address=self.values["addr"].data, i2c=self._bus._ada_i2c)
        except:
            logger.exception("[%s] - Can't start component", self.__class__.__name__)
        finally:
            self._bus.i2c_release()

    def stop(self):
        """
        """
        JNTComponent.stop(self)
        self.sensor = None
