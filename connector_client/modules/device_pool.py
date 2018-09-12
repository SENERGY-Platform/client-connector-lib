"""
   Copyright 2018 SEPL Team

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

try:
    from connector_client.modules.logger import root_logger
    from connector_client.device import DeviceManagerInterface, Device, _isDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

logger = root_logger.getChild(__name__)


class DevicePool(DeviceManagerInterface):
    __pool = dict()

    @staticmethod
    def add(device):
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        if device.id not in __class__.__pool:
            __class__.__pool[device.id] = device
        else:
            logger.warning("device '{}' already in pool".format(device.id))

    @staticmethod
    def update(device):
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        if device.id in __class__.__pool:
            __class__.__pool[device.id] = device
        else:
            logger.error("can't update device '{}' please add it first".format(device.id))

    @staticmethod
    def remove(device):
        if _isDevice(device):
            device = device.id
        elif type(device) is not str:
            raise TypeError("device must be Device, subclass of Device or string (if ID only) but got '{}'".format(type(device)))
        try:
            del __class__.__pool[device]
        except KeyError:
            logger.error("device '{}' does not exist in device pool".format(device))

    @staticmethod
    def get(id_str) -> Device:
        if type(id_str) is not str:
            raise TypeError("id must be a string but got '{}'".format(type(id_str)))
        return __class__.__pool.get(id_str)

    @staticmethod
    def devices() -> dict:
        return __class__.__pool.copy()
