if __name__ == '__main__':
    exit('Please use "client.py"')

import os, configparser

switch = {
    'yes': True,
    'no': False
}

config = configparser.ConfigParser()
config.read('{}/connector.conf'.format(os.getcwd()))

CONNECTOR_PROTOCOL = os.getenv('CONNECTOR_PROTOCOL', config['CONNECTOR']['protocol'])
CONNECTOR_HOST = os.getenv('CONNECTOR_HOST', config['CONNECTOR']['host'])
CONNECTOR_PORT = os.getenv('CONNECTOR_PORT', config['CONNECTOR']['port'])
CONNECTOR_USER = config['CONNECTOR']['user']
CONNECTOR_PASSWORD = config['CONNECTOR']['password']

LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', config['LOGGER']['level'])
LOCAL_ROTATING_LOG = os.getenv('LOCAL_ROTATING_LOG', switch.get(config['LOGGER']['rotating_log']))
ROTATING_LOG_BACKUP_COUNT = os.getenv('ROTATING_LOG_BACKUP_COUNT', config['LOGGER']['rotating_log_backup_count'])
