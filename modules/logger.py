if __name__ == '__main__':
    exit('Please use "client.py"')

from logging.handlers import TimedRotatingFileHandler
import logging, os, configparser



config = configparser.ConfigParser()

if os.path.isfile('{}/connector.conf'.format(os.getcwd())):
    config.read('{}/connector.conf'.format(os.getcwd()))
elif os.path.isfile('{}/connector_client/connector.conf'.format(os.getcwd())):
    config.read('{}/connector_client/connector.conf'.format(os.getcwd()))
else:
    exit('No config file found')

LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', config['LOGGER']['level'])
LOCAL_ROTATING_LOG = os.getenv('LOCAL_ROTATING_LOG', config['LOGGER'].getboolean('rotating_log'))
ROTATING_LOG_BACKUP_COUNT = os.getenv('ROTATING_LOG_BACKUP_COUNT', config['LOGGER']['rotating_log_backup_count'])



logging_levels = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'debug': logging.DEBUG
}


def debug_switch():
    if LOGGING_LEVEL == 'debug':
        return 'name'
    else:
        return 'module'


config_args = {
        'format': '%(asctime)s - %(levelname)s: [%({})s] %(message)s'.format(debug_switch()),
        'datefmt': '%m.%d.%Y %I:%M:%S %p',
        'level': logging_levels[LOGGING_LEVEL],
}


if LOCAL_ROTATING_LOG:
    if not os.path.exists('{}/logs'.format(os.getcwd())):
        os.makedirs('{}/logs'.format(os.getcwd()))
    filename = os.path.join(os.path.dirname(__file__), '{}/logs/connector-client.log'.format(os.getcwd()))
    rotating_log_handler = TimedRotatingFileHandler(filename, when="midnight", backupCount=ROTATING_LOG_BACKUP_COUNT)
    config_args['handlers'] = [rotating_log_handler]
    logging.basicConfig(**config_args)
else:
    logging.basicConfig(**config_args)


root_logger = logging.getLogger()
