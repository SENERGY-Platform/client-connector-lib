if __name__ == '__main__':
    exit('Please use "client.py"')

import os, inspect, configparser



config = configparser.ConfigParser()

try:
    config.read('{}/connector.conf'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))))
except Exception:
    exit('No config file found')


CONNECTOR_PROTOCOL = os.getenv('CONNECTOR_PROTOCOL', config['CONNECTOR']['protocol'])
CONNECTOR_HOST = os.getenv('CONNECTOR_HOST', config['CONNECTOR']['host'])
CONNECTOR_PORT = os.getenv('CONNECTOR_PORT', config['CONNECTOR']['port'])
CONNECTOR_USER = config['CONNECTOR']['user']
CONNECTOR_PASSWORD = config['CONNECTOR']['password']
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', config['LOGGER']['level'])
LOCAL_ROTATING_LOG = os.getenv('LOCAL_ROTATING_LOG', config['LOGGER'].getboolean('rotating_log'))
ROTATING_LOG_BACKUP_COUNT = os.getenv('ROTATING_LOG_BACKUP_COUNT', config['LOGGER']['rotating_log_backup_count'])
