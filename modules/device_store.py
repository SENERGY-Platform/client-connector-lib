if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import sqlite3, os, inspect

logger = root_logger.getChild(__name__)


class DeviceStore:
    _db_path = '{}/devices.db'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))
    _devices_table = 'devices'
    _id_field = ('id', 'TEXT')
    _type_field = ('type', 'TEXT')
    _name_field = ('name', 'TEXT')
    _tags_field = ('tags', 'TEXT')

    def __init__(self):
        if not os.path.isfile(__class__._db_path):
            logger.debug('no database found')
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
            logger.debug('created new database')
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
            tags_v=';'.join(device.tags)
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
                    for key_value in result[2].split(';'):
                        device.addTag(*key_value.split(':', 1))
                except Exception:
                    pass
                return device
        except Exception as ex:
            logger.error(ex)

    def getAll(self) -> dict:
        query = 'SELECT * FROM {table}'.format(
            table=__class__._devices_table
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            self.db_conn.commit()
            devices = dict()
            for item in result:
                device = Device(item[0], item[1], item[2])
                try:
                    for key_value in item[3].split(';'):
                        device.addTag(*key_value.split(':', 1))
                except Exception:
                    pass
                devices[device.id] = device
            return devices
        except Exception as ex:
            logger.error(ex)

    def getIDs(self) -> list:
        query = 'SELECT {id} FROM {table}'.format(
            id=__class__._id_field[0],
            table=__class__._devices_table
        )
        try:
            logger.debug(query)
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            self.db_conn.commit()
            return [item[0] for item in result]
        except Exception as ex:
            logger.error(ex)
