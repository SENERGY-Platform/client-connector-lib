if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import SimpleSingleton
    from connector.device import DeviceManagerInterface, Device, _isDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import inspect
import os
import sqlite3

logger = root_logger.getChild(__name__)


class DeviceStore(DeviceManagerInterface, SimpleSingleton):
    _db_path = '{}/devices.sqlite'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
    _devices_table = 'devices'
    _id_field = ('id', 'TEXT')
    _type_field = ('type', 'TEXT')
    _name_field = ('name', 'TEXT')
    _tags_field = ('tags', 'TEXT')

    def __init__(self):
        if not os.path.isfile(__class__._db_path):
            logger.debug('no database found')
            query = 'CREATE TABLE {table} ({id} {id_t} PRIMARY KEY, {type} {type_t}, {name} {name_t}, {tags} {tags_t})'.format(
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
            self._executeQuery(query)
            logger.debug('created new database')
        else:
            logger.debug("found database at '{}'".format(__class__._db_path))

    def _executeQuery(self, query):
        try:
            db_conn = sqlite3.connect(__class__._db_path)
            cursor = db_conn.cursor()
            cursor.execute(query)
            if any(statement in query for statement in ('CREATE', 'INSERT', 'DELETE', 'UPDATE')):
                db_conn.commit()
                result = True
            else:
                result = cursor.fetchall()
            db_conn.close()
            return result
        except Exception as ex:
            logger.error(ex)
            return False

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
            tags_v=';'.join(device.tags)
        )
        self._executeQuery(query)

    def remove(self, d_id):
        if type(d_id) is Device:
            d_id = d_id.id
        elif type(d_id) is not str:
            raise TypeError("a string or a Device object must be provided but got a '{}'".format(type(d_id)))
        query = 'DELETE FROM {table} WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            id=__class__._id_field[0],
            id_v=d_id
        )
        self._executeQuery(query)

    def update(self, device):
        if type(device) is not Device:
            raise TypeError("a Device object must be provided but got a '{}'".format(type(device)))
        query = 'UPDATE {table} SET {type}="{type_v}", {name}="{name_v}", {tags}="{tags_v}" WHERE {id}="{id_v}"'.format(
            table=__class__._devices_table,
            type=__class__._type_field[0],
            type_v=device.type,
            name=__class__._name_field[0],
            name_v=device.name,
            tags=__class__._tags_field[0],
            tags_v=';'.join(device.tags),
            id=__class__._id_field[0],
            id_v=device.id
        )
        self._executeQuery(query)

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
        result = self._executeQuery(query)
        if result:
            device = Device(id_str, result[0][0], result[0][1])
            try:
                for key_value in result[0][2].split(';'):
                    device.addTag(*key_value.split(':', 1))
            except Exception as ex:
                logger.error(ex)
            return device

    def devices(self) -> dict:
        query = 'SELECT * FROM {table}'.format(
            table=__class__._devices_table
        )
        result = self._executeQuery(query)
        devices = dict()
        for item in result:
            device = Device(item[0], item[1], item[2])
            try:
                for key_value in item[3].split(';'):
                    device.addTag(*key_value.split(':', 1))
            except Exception as ex:
                logger.error(ex)
            devices[device.id] = device
        return devices
