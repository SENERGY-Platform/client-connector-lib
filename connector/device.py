if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import hashlib
from collections import OrderedDict
from abc import ABCMeta, abstractmethod

logger = root_logger.getChild(__name__)


def _isDevice(obj):
    """
    Check if a object is a Device or a Device subclass
    :param obj: object to check
    :return: Boolean
    """
    if type(obj) is Device or issubclass(type(obj), Device):
        return True
    return False


class Device:
    """
    Use this class to create devices for use with the connector-client.
    Subclass this class for advanced requirements. Don't forget to call __init__ of this class when subclassing.
    """
    def __init__(self, id, type, name):
        """
        Create a device object. Checks if parameters meet type requirements.
        :param id: Local device ID.
        :param type: Device type (create device types via SEPL gui).
        :param name: Device name.
        :return: Device object
        """
        __class__.__checkType(id)
        __class__.__checkType(type)
        __class__.__checkType(name)
        self.__id = id
        self.__type = type
        self.__name = name
        self.__tags = OrderedDict()

    @property
    def id(self) -> str:
        return self.__id

    @property
    def type(self) -> str:
        return self.__type

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, arg):
        if type(arg) is not str:
            raise TypeError("name must be a string but got '{}'".format(type(arg)))
        self.__name = arg

    @property
    def tags(self) -> list:
        """
        Combine tag IDs and tags as key:value pairs.
        :return: List.
        """
        return ['{}:{}'.format(key, value) for key, value in self.__tags.items()]

    @property
    def hash(self) -> str:
        """
        Uses device attributes to calculate a sha1 hash.
        :return: String.
        """
        return hashlib.sha1(''.join((self.__id, self.__type, self.__name, ''.join(['{}{}'.format(key, value) for key, value in self.__tags.items()]))).encode()).hexdigest()

    def addTag(self, tag_id, tag):
        """
        Add a tag to a device.
        :param: tag_id: ID identifying the tag.
        :param: tag: Word or combination of Words.
        :return: Boolean
        """
        if type(tag_id) is not str:
            raise TypeError("tag id must be a string but got '{}'".format(type(tag_id)))
        if type(tag) is not str:
            raise TypeError("tag must be a string but got '{}'".format(type(tag)))
        if tag_id in ('device_name', 'device_type'):
            raise TypeError("tag id '{}' already in use".format(type(tag_id)))
        if ':' in tag_id or ';' in tag_id:
            raise ValueError("tag id may not contain ':' or ';'")
        if ':' in tag or ';' in tag:
            raise ValueError("tag may not contain ':' or ';'")
        self.__tags[tag_id] = tag
        return True

    def changeTag(self, tag_id, tag):
        """
        Change existing tag.
        :param: tag_id: ID identifying the tag.
        :param: tag: Word or combination of Words.
        :return: Boolean
        """
        if ':' in tag or ';' in tag:
            raise ValueError("tag may not contain ':' or ';'")
        if tag_id in self.__tags:
            self.__tags[tag_id] = tag
            return True
        logger.error("tag id ‘{}‘ does not exist".format(tag_id))
        return False

    def removeTag(self, tag_id):
        """
        Remove existing tag.
        :param: tag_id: ID identifying the tag.
        :return: Boolean
        """
        try:
            del(self.__tags[tag_id])
            return True
        except KeyError:
            logger.error("tag id ‘{}‘ does not exist".format(tag_id))
            return False

    @staticmethod
    def __checkType(arg):
        """
        Check if type is string. Raise exception if not.
        :param: arg: object to check
        """
        if type(arg) is not str:
            raise TypeError("'{}' must be a string but is a '{}'".format(arg, type(arg)))

    def __repr__(self, **kwargs):
        """
        Provide a string representation.
        :param kwargs: User attributes provided from subclass.
        :return: String.
        """
        attributes = {
            'id': self.id,
            'type': self.type,
            'name': self.name,
            'tags': self.tags,
            'hash': self.hash
        }
        if kwargs:
            for key, arg in kwargs.items():
                attributes[key] = arg
        return "{}({})".format(type(self).__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes.items()]))


class DeviceManagerInterface(metaclass=ABCMeta):
    """
    Interface class. Device managers must inherit from this class.
    """
    @abstractmethod
    def add(*sc, device):
        """
        add device
        :param device: takes a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def update(*sc, device):
        """
        update device
        :param device: takes a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def remove(*sc, id_str):
        """
        remove device
        :param id_str: takes device ID as string.
        """
        pass

    @abstractmethod
    def get(*sc, id_str):
        """
        get device
        :param id_str: takes device ID as string.
        :return a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def devices(*sc, _):
        """
        all devices
        :param _: don't use
        :return a dict, list or tuple object.
        """
        pass
