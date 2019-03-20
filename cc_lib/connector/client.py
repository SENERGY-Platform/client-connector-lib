"""
   Copyright 2019 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

__all__ = ('Client', )

from cc_lib import __version__ as VERSION
from ..configuration.configuration import cc_conf, initConnectorConf
from ..logger.logger import _getLibLogger, initLogging
from .singleton import Singleton
from ..device.manager.interface import Interface
from inspect import isclass
from typing import Callable
from threading import Thread


logger = _getLibLogger(__name__.split('.', 1)[-1])


class ClientError(Exception):
    """
    Base error.
    """
    pass


class NoDeviceMgrError(ClientError):
    """
    No device manager was found.
    """
    def __init__(self):
        super().__init__(
            "missing device manager - use '{}' before calling '{}' method".format(
                Client.setDeviceManager.__name__,
                Client.start.__name__
            )
        )

class DeviceMgrSetError(ClientError):
    """
    Device manager already set.
    """
    def __init__(self):
        super().__init__("device manager already set")


def _interfaceCheck(cls, interface):
    """
    Check if a class subclasses another class.
    Raise TypeError on mismatch.
    :param cls: Class to check.
    :param interface: Class that should be subclassed.
    :return: Boolean.
    """
    if issubclass(cls, interface):
        return True
    raise TypeError("provided class '{}' must be a subclass of '{}'".format(cls, interface))


class Client(metaclass=Singleton):
    """
    Client class for client-connector projects.
    To avoid multiple instantiations the Client class implements the singleton pattern.
    Threading is managed internally, wrapping the client in a thread is not necessary.
    """

    def __init__(self, device_manager: Interface = None):
        """
        Create a Client instance. Initiate configuration and library logging facility.
        :param device_manager: object or class implementing the device manager interface.
        """
        self.__device_manager: Interface = None
        if device_manager:
            self.setDeviceManager(device_manager)
        initConnectorConf()
        initLogging()

    def __start(self, async_cb=None):
        """
        Start the client.
        :param async_cb: Callback function to be executed after startup.
        :return: None.
        """
        logger.info(12 * '-' + ' Starting client-connector v{} '.format(VERSION) + 12 * '-')
        # provision hub
        # start mqtt client
        if async_cb:
            async_cb()

    # ------------- user methods ------------- #

    def setDeviceManager(self, mgr: Interface) -> None:
        """
        Check if provided object or class implements the device manager interface and sets the respective attribute.
        :param mgr: object or class implementing the device manager interface.
        :return: None.
        """
        if self.__device_manager:
            raise DeviceMgrSetError
        if isclass(mgr):
            if not _interfaceCheck(mgr, Interface):
                raise TypeError("'{}' must subclass device manager interface".format(mgr.__name__))
        else:
            if not _interfaceCheck(type(mgr), Interface):
                raise TypeError("'{}' must subclass device manager interface".format(type(mgr).__name__))
        self.__device_manager = mgr

    def start(self, async_clbk: Callable[[], None] = None) -> None:
        """
        Check if a device manager is present. Will block if async_clbk isn't provided.
        Call internal start method to start the client.
        :param async_clbk: Callback function to be executed after startup.
        :return: None.
        """
        if not self.__device_manager:
            raise NoDeviceMgrError
        if async_clbk:
            start_thread = Thread(target=self.__start, args=(async_clbk, ), name='Starter')
            start_thread.start()
        else:
            self.__start()


    def emmitEvent(self):
        pass

    def receiveCommand(self):
        pass

    def sendResponse(self):
        pass

    def addDevice(self):
        pass

    def deleteDevice(self):
        pass

    def connectDevice(self):
        pass

    def disconnectDevice(self):
        pass
