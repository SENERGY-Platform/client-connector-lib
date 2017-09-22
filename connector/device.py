if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import hashlib
from collections import OrderedDict

logger = root_logger.getChild(__name__)


class Device:
    def __init__(self, id, type, name):
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

    @id.setter
    def id(self, arg):
        raise TypeError("attribute id is immutable")

    @property
    def type(self) -> str:
        return self.__type

    @type.setter
    def type(self, arg):
        raise TypeError("attribute type is immutable")

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
        return ['{}:{}'.format(key, value) for key, value in self.__tags.items()]

    @tags.setter
    def tags(self, arg):
        raise TypeError("attribute tags is immutable - use addTag, changeTag or removeTag")

    @property
    def hash(self) -> str:
        return hashlib.sha1(''.join((self.__id, self.__type, self.__name, ''.join(['{}{}'.format(key, value) for key, value in self.__tags.items()]))).encode()).hexdigest()

    @hash.setter
    def hash(self, arg):
        raise TypeError("attribute hash is immutable")

    def addTag(self, tag_id, tag):
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
        if ':' in tag or ';' in tag:
            raise ValueError("tag may not contain ':' or ';'")
        if tag_id in self.__tags:
            self.__tags[tag_id] = tag
            return True
        return False

    def removeTag(self, tag_id):
        try:
            del(self.__tags[tag_id])
            return True
        except KeyError:
            logger.error("tag id ‘{}‘ does not exist".format(tag_id))
            return False

    @staticmethod
    def __checkType(arg):
        if type(arg) is not str:
            raise TypeError("'{}' must be a string but is a '{}'".format(arg, type(arg)))
