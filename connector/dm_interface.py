if __name__ == '__main__':
    exit('Please use "service.py"')

from abc import ABCMeta, abstractmethod


class DeviceManagerInterface(metaclass=ABCMeta):
    """
    Interface class. Device managers must inherit from this class.
    """
    @abstractmethod
    def add(self, device):
        """
        add device
        :param device: takes a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def update(self, device):
        """
        update device
        :param device: takes a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def remove(self, id_str):
        """
        add device
        :param id_str: takes device ID as string.
        """
        pass

    @abstractmethod
    def get(self, id_str):
        """
        get device
        :param id_str: takes device ID as string.
        :return a Device (or subclass of Device) object.
        """
        pass

    @property
    @abstractmethod
    def devices(self):
        """
        all devices
        :return a dict, list or tuple object.
        """
        pass
