if __name__ == '__main__':
    exit('Please use "client.py"')

import os, inspect, configparser


init_path = '{}/__init__.py'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))

def read_version():
    values = dict()
    with open(init_path, 'r') as init_file:
        exec(init_file.read(), values)
    return values.get('__version__')

USER_PATH = '{}/sepl-connector-client'.format(os.getcwd())

if not os.path.exists(USER_PATH):
    os.makedirs(USER_PATH)

config = configparser.ConfigParser()

conf_file_path = '{}/client.conf'.format(USER_PATH)

if not os.path.isfile(conf_file_path):
    print('No config file found')
    config['CONNECTOR'] = {
        'encryption': 'no',
        'host': '',
        'port': '',
        'user': '',
        'password': '',
        'gid': ''
    }
    config['LOGGER'] = {
        'level': 'debug',
        'rotating_log': 'no',
        'rotating_log_backup_count': 14
    }
    with open(conf_file_path, 'w') as conf_file:
        config.write(conf_file)
    exit('Created blank config file')


try:
    config.read(conf_file_path)
except Exception as ex:
    exit(ex)


def writeConf(section, option, value):
    config.set(section=section, option=option, value=value)
    try:
        with open(conf_file_path, 'w') as conf_file:
            config.write(conf_file)
    except Exception as ex:
        print(ex)


protocol_map = {
    'yes': 'wss',
    'no': 'ws'
}


CONNECTOR_WS_ENCRYPTION = protocol_map[config['CONNECTOR']['encryption']]
CONNECTOR_WS_HOST = config['CONNECTOR']['host']
CONNECTOR_WS_PORT = config['CONNECTOR']['port']
CONNECTOR_USER = config['CONNECTOR']['user']
CONNECTOR_PASSWORD = config['CONNECTOR']['password']
GATEWAY_ID = config['CONNECTOR']['gid']
LOGGING_LEVEL = os.getenv('CONNECTOR_CLIENT_LOG_LEVEL', config['LOGGER']['level'])
LOCAL_ROTATING_LOG = config['LOGGER'].getboolean('rotating_log')
ROTATING_LOG_BACKUP_COUNT = config['LOGGER']['rotating_log_backup_count']
L_FORMAT = os.environ.get('L_FORMAT')
VERSION = read_version()