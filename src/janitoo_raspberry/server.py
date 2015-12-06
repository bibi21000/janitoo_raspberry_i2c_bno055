# -*- coding: utf-8 -*-
"""The Raspberry server

Define one controller
A node for camera
A node with multiple vales or multiple nodes for i2c
...
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

import platform

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)
import os, sys
import threading
from pkg_resources import get_distribution, DistributionNotFound
from janitoo.mqtt import MQTTClient
from janitoo.server import JNTServer, JNTControllerManager
from janitoo.utils import JanitooException

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_UPDATE = 0x1040
COMMAND_CONTROLLER = 0x1050
COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
assert(COMMAND_DESC[COMMAND_CONTROLLER] == 'COMMAND_CONTROLLER')
assert(COMMAND_DESC[COMMAND_UPDATE] == 'COMMAND_UPDATE')
##############################################################

class PiServer(JNTServer, JNTControllerManager):
    """The Raspberry pi Server

    """
    def __init__(self, options, check_plateform=False):
        """
        """
        #Check that we are on a raspberry
        if check_plateform==True and not platform.machine().startswith('armv6'):
            raise JanitooException(message='This server can be used on Raspberry Pi only')
        JNTServer.__init__(self, options)
        self.section = "raspi"
        JNTControllerManager.__init__(self)

    def _get_egg_path(self):
        """Return the egg path of the module. Must be redefined in server class. Used to find alembic migration scripts.
        """
        try:
            _dist = get_distribution('janitoo_pi')
            return _dist.__file__
        except AttributeError:
            return os.path.join("/opt/janitoo/src",'src-pi/config')

    def start(self):
        """Start the DHCP Server
        """
        JNTServer.start(self)
        JNTControllerManager.start_controller(self, self.section, self.options, cmd_classes=[COMMAND_UPDATE], hadd=None, name="Raspberry Pi Server",
            product_name="Raspberry Pi Server", product_type="Raspberry Pi Server")
        JNTControllerManager.start_controller_timer(self)

    def stop(self):
        """Stop the DHCP Server
        """
        JNTControllerManager.stop_controller_timer(self)
        JNTControllerManager.stop_controller(self)
        JNTServer.stop(self)
