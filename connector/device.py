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
        self.id = id
        self.type = type
        self.name = name


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
            db_conn = sqlite3.connect(__class__._db_path)
            self.cursor = db_conn.cursor()
            self.cursor.execute(init_query)
            logger.info('created new database')
        else:
            logger.debug("found database at '{}'".format(__class__._db_path))
            db_conn = sqlite3.connect(__class__._db_path)
            self.cursor = db_conn.cursor()
            logger.info('loaded database')

    def add(self, device):
        query = 'INSERT INTO {table} ({id}, {type}, {name}) VALUES ({id_v}, {type_v}, "{name_v}")'.format(
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
        except sqlite3.IntegrityError:
            logger.error("device '{}' already exists".format(device.id))

    def remove(self, device):
        pass

    def update(self, device):
        pass

    def get(self, id):
        pass


