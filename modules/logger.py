if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from connector.configuration import LOGLEVEL, LOCAL_ROTATING_LOG, ROTATING_LOG_BACKUP_COUNT
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from logging.handlers import TimedRotatingFileHandler
import logging, os


logging_levels = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'debug': logging.DEBUG
}


def debug_switch():
    if LOGLEVEL == 'debug':
        return 'name'
    else:
        return 'module'


config_args = {
        'format': '%(asctime)s - %(levelname)s: [%({})s] %(message)s'.format(debug_switch()),
        'datefmt': '%m.%d.%Y %I:%M:%S %p',
        'level': logging_levels[LOGLEVEL],
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
