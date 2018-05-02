if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from connector.configuration import LOGGING_LEVEL, LOCAL_ROTATING_LOG, ROTATING_LOG_BACKUP_COUNT
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from logging.handlers import TimedRotatingFileHandler
import logging, os, inspect


logging_levels = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'debug': logging.DEBUG
}


formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s: [%(name)s] %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p')

root_logger = logging.getLogger("sepl")
root_logger.propagate = False
root_logger.setLevel(logging_levels[LOGGING_LEVEL])

connector_client_log_handler = logging.StreamHandler()

if LOCAL_ROTATING_LOG:
    logger_path = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
    logs_path = '{}/logs'.format(os.path.split(logger_path)[0])
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)
    file_path = os.path.join(os.path.dirname(__file__), '{}/connector-client.log'.format(logs_path))
    connector_client_log_handler = TimedRotatingFileHandler(file_path, when="midnight", backupCount=int(ROTATING_LOG_BACKUP_COUNT))

connector_client_log_handler.setFormatter(formatter)
root_logger.addHandler(connector_client_log_handler)