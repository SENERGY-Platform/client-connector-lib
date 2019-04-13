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

from ..logger.logger import _getLibLogger
from ..device.device import Device
from typing import Tuple
from threading import Lock


logger = _getLibLogger(__name__)


def isDevice(obj: object) -> bool:
    """
    Check if a object is a Device or a Device subclass
    :param obj: object to check
    :return: Boolean
    """
    if type(obj) is Device or issubclass(type(obj), Device):
        return True
    return False


class DeviceManager:

    def __init__(self):
        self.__device_pool = dict()
        self.__lock = Lock()

    def add(self, device: Device) -> None:
        if not isDevice(device):
            raise TypeError
        self.__lock.acquire()
        if device.id not in self.__device_pool:
            self.__device_pool[device.id] = device
        else:
            logger.warning("device '{}' already in pool".format(device.id))
        self.__lock.release()

    def delete(self, device_id: str) -> None:
        if not type(device_id) is str:
            raise TypeError
        self.__lock.acquire()
        try:
            del self.__device_pool[device_id]
        except KeyError:
            logger.warning("device '{}' does not exist in device pool".format(device_id))
        self.__lock.release()

    def get(self, device_id: str) -> Device:
        if type(device_id) is not str:
            raise TypeError
        self.__lock.acquire()
        try:
            device = self.__device_pool[device_id]
        except KeyError:
            logger.error("device '{}' not in pool".format(device_id))
            self.__lock.release()
            raise
        self.__lock.release()
        return device

    def clear(self) -> None:
        self.__lock.acquire()
        self.__device_pool.clear()
        self.__lock.release()

    @property
    def devices(self) -> Tuple[Device]:
        self.__lock.acquire()
        devices = tuple(self.__device_pool.values())
        self.__lock.release()
        return devices
