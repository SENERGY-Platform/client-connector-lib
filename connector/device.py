if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import sqlite3, os, inspect

logger = root_logger.getChild(__name__)


class Device:
    def __init__(self, id, type, name):
        __class__.__checkType(id)
        __class__.__checkType(type)
        __class__.__checkType(name)
        self.__id = id
        self.__type = type
        self.__name = name
        #self.__std_tags = ['device_name:{}'.format(self.__name), 'device_type:{}'.format(self.__type)]
        self.__tags = dict()

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, arg):
        raise TypeError("attribute id is immutable")

    @property
    def type(self):
        return self.__type

    @type.setter
    def type(self, arg):
        raise TypeError("attribute type is immutable")

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, arg):
        if type(arg) is not str:
            raise TypeError("name must be a string but got '{}'".format(type(arg)))
        self.__name = arg

    @property
    def tags(self):
        return ['{}:{}'.format(key, value) for key, value in self.__tags.items()]

    @tags.setter
    def tags(self, arg):
        raise TypeError("attribute tags is immutable - use addTag, changeTag or removeTag")

    def addTag(self, tag_id, tag):
        if type(tag_id) is not str:
            raise TypeError("tag id must be a string but got '{}'".format(type(tag_id)))
        if type(tag) is not str:
            raise TypeError("tag must be a string but got '{}'".format(type(tag)))
        if tag_id in ('device_name', 'device_type'):
            raise TypeError("tag id '{}' already in use".format(type(tag_id)))
        if ':' in tag_id:
            raise ValueError("tag id may not contain ':'")
        self.__tags[tag_id] = tag
        return True

    def changeTag(self, tag_id, tag):
        if type(tag) is not str:
            raise TypeError("tag must be a string but got '{}'".format(type(tag)))
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


class DeviceManager:
    _db_path = '{}/devices.db'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
    _devices_table = 'devices'
    _id_field = ('id', 'TEXT')
    _type_field = ('type', 'TEXT')
    _name_field = ('name', 'TEXT')
    _tags_field = ('tags', 'TEXT')

    def __init__(self):
        if not os.path.isfile(__class__._db_path):
            logger.info('no database found')
            init_query = 'CREATE TABLE {table} ({id} {id_t} PRIMARY KEY, {type} {type_t}, {name} {name_t}, {tags} {tags_t})'.format(
                    table=__class__._devices_table,
                    id=__class__._id_field[0],
                    id_t=__class__._id_field[1],
                    type=__class__._type_field[0],
                    type_t=__class__._type_field[1],
                    name=__class__._name_field[0],
                    name_t=__class__._name_field[1],
                    tags=__class__._tags_field[0],
                    tags_t=__class__._tags_field[1]
                )
            self.db_conn = sqlite3.connect(__class__._db_path)
            self.cursor = self.db_conn.cursor()
            self.cursor.execute(init_query)
            self.db_conn.commit()
            logger.info('created new database')
        else:
            logger.debug("found database at '{}'".format(__class__._db_path))
            self.db_conn = sqlite3.connect(__class__._db_path)
            self.cursor = self.db_conn.cursor()

    def add(self, device):
        if type(device) is not Device:
            raise TypeError("a Device object must be provided but got a '{}'".format(type(device)))
        query = 'INSERT INTO {table} ({id}, {type}, {name}, {tags}) VALUES ("{id_v}", "{type_v}", "{name_v}", "{tags_v}")'.format(
            table=__class__._devices_table,
            id=__class__._id_field[0],
            id_v=device.id,
            type=__class__._type_field[0],
            type_v=device.type,
            name=__class__._name_field[0],
            name_v=device.name,
            tags=__class__._tags_field[0],
            tags_v=device.tags
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            self.db_conn.commit()
        except Exception as ex:
            logger.error(ex)

    def remove(self, device):
        if type(device) is Device:
            d_id = device.id
        elif type(device) is str:
            d_id = device
        else:
            raise TypeError("a string or a Device object must be provided but got a '{}'".format(type(device)))
        query = 'DELETE FROM {table} WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            id=__class__._id_field[0],
            id_v=d_id
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            self.db_conn.commit()
        except Exception as ex:
            logger.error(ex)

    def update(self, device):
        if type(device) is not Device:
            raise TypeError("a Device object must be provided but got a '{}'".format(type(device)))
        query = 'UPDATE {table} SET {type}="{type_v}", {name}="{name_v}" WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            type=__class__._type_field[0],
            type_v=device.type,
            name=__class__._name_field[0],
            name_v=device.name,
            id=__class__._id_field[0],
            id_v=device.id
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            self.db_conn.commit()
        except Exception as ex:
            logger.error(ex)

    def get(self, id_str) -> Device:
        if type(id_str) is not str:
            raise TypeError("id must be a string but got '{}'".format(type(id_str)))
        query = 'SELECT {type}, {name}, {tags} FROM {table} WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            type=__class__._type_field[0],
            name=__class__._name_field[0],
            tags=__class__._tags_field[0],
            id=__class__._id_field[0],
            id_v=id_str
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            self.db_conn.commit()
            if result:
                device = Device(id_str, result[0], result[1])
                try:
                    for key_value in result[2]:
                        device.addTag(*key_value.split(':', 1))
                except Exception:
                    pass
                return device
            else:
                logger.error("device '{}' does not exist".format(id_str))
        except Exception as ex:
            logger.error(ex)

    def dump(self) -> list:
        query = 'SELECT * FROM {table}'.format(
            id=__class__._id_field[0],
            table=__class__._devices_table
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            self.db_conn.commit()
            return result
        except Exception as ex:
            logger.error(ex)
