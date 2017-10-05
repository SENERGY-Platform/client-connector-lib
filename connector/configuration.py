if __name__ == '__main__':
    exit('Please use "client.py"')

import os, inspect, configparser



config = configparser.ConfigParser()

try:
    config.read('{}/connector.conf'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))))
except Exception:
    exit('No config file found')


def writeConf(parameter, value, section=None):
    if section:
        config[section][parameter] = value
    else:
        config[parameter] = value


CONNECTOR_PROTOCOL = config['CONNECTOR']['protocol']
CONNECTOR_HOST = config['CONNECTOR']['host']
CONNECTOR_PORT = config['CONNECTOR']['port']
CONNECTOR_USER = config['CONNECTOR']['user']
CONNECTOR_PASSWORD = config['CONNECTOR']['password']
CONNECTOR_GID = config['CONNECTOR']['gid']
LOGGING_LEVEL = os.getenv('CONNECTOR_CLIENT_LOG_LEVEL', config['LOGGER']['level'])
LOCAL_ROTATING_LOG = config['LOGGER'].getboolean('rotating_log')
ROTATING_LOG_BACKUP_COUNT = config['LOGGER']['rotating_log_backup_count']