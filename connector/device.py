if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import sqlite3, os

logger = root_logger.getChild(__name__)


class Device():
    def __init__(self, id, type, name):
        self.__id = id
        self.type = type
        self.name = name

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, arg):
        raise TypeError("attribute id is immutable")


class DeviceManager(metaclass=Singleton):
    _db_path = '{}/connector/devices.db'.format(os.getcwd())
    _devices_table = 'devices'
    _id_field = ('id', 'TEXT')
    _type_field = ('type', 'TEXT')
    _name_field = ('name', 'TEXT')

    def __init__(self):
        if not os.path.isfile(__class__._db_path):
            logger.info('no database found')
            init_query = 'CREATE TABLE {table} ({id} {id_t} PRIMARY KEY, {type} {type_t}, {name} {name_t})'.format(
                    table=__class__._devices_table,
                    id=__class__._id_field[0],
                    id_t=__class__._id_field[1],
                    type=__class__._type_field[0],
                    type_t=__class__._type_field[1],
                    name=__class__._name_field[0],
                    name_t=__class__._name_field[1]
                )
            self.db_conn = sqlite3.connect(__class__._db_path)
            self.cursor = self.db_conn.cursor()
            self.cursor.execute(init_query)
            logger.info('created new database')
        else:
            logger.debug("found database at '{}'".format(__class__._db_path))
            self.db_conn = sqlite3.connect(__class__._db_path)
            self.cursor = self.db_conn.cursor()
            logger.info('loaded database')

    def add(self, device):
        query = 'INSERT INTO {table} ({id}, {type}, {name}) VALUES ("{id_v}", "{type_v}", "{name_v}")'.format(
            table=__class__._devices_table,
            id=__class__._id_field[0],
            id_v=device.id,
            type=__class__._type_field[0],
            type_v=device.type,
            name=__class__._name_field[0],
            name_v=device.name
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            self.db_conn.commit()
        except sqlite3.IntegrityError:
            logger.error("device '{}' already exists".format(device.id))

    def remove(self, device):
        query = 'DELETE FROM {table} WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            id=__class__._id_field[0],
            id_v=device.id
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            self.db_conn.commit()
        except sqlite3.IntegrityError:
            logger.error("device '{}' not found".format(device.id))

    def update(self, device):
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
        except sqlite3.IntegrityError:
            logger.error("device '{}' not found".format(device.id))

    def get(self, id_str):
        if type(id_str) is not str:
            raise TypeError("id must be a string but got '{}'".format(type(id_str)))
        query = 'SELECT {type}, {name} FROM {table} WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            type=__class__._type_field[0],
            name=__class__._name_field[0],
            id=__class__._id_field[0],
            id_v=id_str
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            self.db_conn.commit()
            result = self.cursor.fetchone()
            return Device(id_str, result[0], result[1])
        except sqlite3.IntegrityError:
            logger.error("device '{}' not found".format(id_str))
