if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import SimpleSingleton
    from connector.dm_interface import DeviceManagerInterface
    from connector.device import Device, _isDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

logger = root_logger.getChild(__name__)


class DevicePool(DeviceManagerInterface, SimpleSingleton):
    __pool = dict()

    def add(self, device):
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        if device.id not in __class__.__pool:
            __class__.__pool[device.id] = device
        else:
            logger.warning("device '{}' already in pool".format(device.id))

    def update(self, device):
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        if device.id in __class__.__pool:
            __class__.__pool[device.id] = device
        else:
            logger.error("can't update device '{}' please add it first".format(device.id))

    def remove(self, device):
        if _isDevice(device):
            device = device.id
        elif type(device) is not str:
            raise TypeError("device must be Device, subclass of Device or string (if ID only) but got '{}'".format(type(device)))
        try:
            del __class__.__pool[device]
        except KeyError:
            logger.error("device '{}' does not exist in device pool".format(device))

    def get(self, id_str) -> Device:
        if type(id_str) is not str:
            raise TypeError("id must be a string but got '{}'".format(type(id_str)))
        return __class__.__pool.get(id_str)

    @property
    def devices(self) -> dict:
        return __class__.__pool.copy()
