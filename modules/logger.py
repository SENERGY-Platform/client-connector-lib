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


if not os.path.exists('{}/logs'.format(os.getcwd())):
    os.makedirs('{}/logs'.format(os.getcwd()))
filename = os.path.join(os.path.dirname(__file__), '{}/logs/connector-client.log'.format(os.getcwd()))
rotating_log_handler = TimedRotatingFileHandler(filename, when="midnight", backupCount=ROTATING_LOG_BACKUP_COUNT)


if LOCAL_ROTATING_LOG:

    logging.basicConfig(
        format='%(asctime)s - %(levelname)s: [%(module)s] %(message)s',
        datefmt='%m.%d.%Y %I:%M:%S %p',
        level=logging_levels[LOGLEVEL],
        handlers=[rotating_log_handler]
    )
else:
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s: [%(module)s] %(message)s',
        datefmt='%m.%d.%Y %I:%M:%S %p',
        level=logging_levels[LOGLEVEL]
    )


root_logger = logging.getLogger()
