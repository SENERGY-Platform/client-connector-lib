if __name__ == '__main__':
    exit('Please use "service.py"')

try:
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from abc import ABCMeta, abstractmethod


class DeviceManagerInterface(metaclass=ABCMeta):
    """
    Interface class. Device managers must inherit from this class.
    """
    @abstractmethod
    def add(self, device):
        pass

    @abstractmethod
    def update(self, device):
        pass

    @abstractmethod
    def remove(self, d_id):
        pass

    @abstractmethod
    def get(self, id_str) -> Device:
        pass

    @property
    @abstractmethod
    def devices(self) -> dict:
        pass
