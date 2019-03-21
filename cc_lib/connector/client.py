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


class DeviceMgrSetError(ClientError):
    """
    Device manager can't be set.
    """
    __cases = {
        1: "provided class '{}' does not implement the device manager interface",
        2: "the class '{}' of the provided object does not implement the device manager interface"
    }

    def __init__(self, case, *args):
        super().__init__(__class__.__cases[case].format(*args))


class Client(metaclass=Singleton):
    """
    Client class for client-connector projects.
    To avoid multiple instantiations the Client class implements the singleton pattern.
    Threading is managed internally, wrapping the client in a thread is not necessary.
    """

    def __init__(self, device_manager: Interface):
        """
        Create a Client instance. Set device manager, initiate configuration and library logging facility.
        :param device_manager: object or class implementing the device manager interface.
        """
        self.__device_manager = self.__checkDeviceManager(device_manager)
        initConnectorConf()
        initLogging()

    def __checkDeviceManager(self, mgr) -> Interface:
        """
        Check if provided object or class implements the device manager interface.
        :param mgr: object or class.
        :return: object or class implementing the device manager interface.
        """
        if isclass(mgr):
            if not issubclass(mgr, Interface):
                raise DeviceMgrSetError(1, mgr.__name__)
        else:
            if not issubclass(type(mgr), Interface):
                raise DeviceMgrSetError(2, type(mgr).__name__)
        return mgr

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

    def start(self, async_clbk: Callable[[], None] = None) -> None:
        """
        Check if a device manager is present. Will block if async_clbk isn't provided.
        Call internal start method to start the client.
        :param async_clbk: Callback function to be executed after startup.
        :return: None.
        """
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
