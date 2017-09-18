if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

logger = root_logger.getChild(__name__)


class DevicePool(metaclass=Singleton):
    _pool = dict()

    @staticmethod
    def add(device):
        if type(device) is not Device:
            raise TypeError("a Device object must be provided but got a '{}'".format(type(device)))
        if device.id not in __class__._pool:
            __class__._pool[device.id] = device
        else:
            logger.warning("device '{}' already in pool".format(device.id))

    @staticmethod
    def update(device):
        if type(device) is not Device:
            raise TypeError("a Device object must be provided but got a '{}'".format(type(device)))
        if device.id in __class__._pool:
            __class__._pool[device.id] = device
        else:
            logger.error("can't update device '{}' please add it first".format(device.id))

    @staticmethod
    def remove(d_id):
        try:
            del __class__._pool[d_id]
        except KeyError:
            logger.error("device '{}' does not exist in device pool".format(d_id))

    @staticmethod
    def get(id_str) -> Device:
        if type(id_str) is not str:
            raise TypeError("id must be a string but got '{}'".format(type(id_str)))
        return __class__._pool.get(id_str)

    @staticmethod
    def dump() -> dict:
        return __class__._pool.copy()

    '''
    @staticmethod
    def lsIDs() -> list:
        return [device.id for device in __class__._pool.values()]

    @staticmethod
    def ls() -> list:
        return list(__class__._pool.values())
    '''
