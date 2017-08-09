if __name__ == '__main__':
    exit('Please use "client.py"')

from logging.handlers import TimedRotatingFileHandler
import logging, os


LOGLEVEL = os.getenv('LOGGING_LEVEL', 'info')
LOCAL_ROTATING_LOG = os.getenv('LOCAL_ROTATING_LOG', None)
ROTATING_LOG_BACKUP_COUNT = os.getenv('ROTATING_LOG_BACKUP_COUNT', 7)


logging_levels = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'debug': logging.DEBUG
}


filename = os.path.join(os.path.dirname(__file__), '../connector-client.log')
rotating_log_handler = TimedRotatingFileHandler(filename, when="midnight", backupCount=ROTATING_LOG_BACKUP_COUNT)


if LOCAL_ROTATING_LOG:
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s: [%(name)s] %(message)s',
        datefmt='%m.%d.%Y %I:%M:%S %p',
        level=logging_levels[LOGLEVEL],
        handlers=[rotating_log_handler]
    )
else:
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s: [%(name)s] %(message)s',
        datefmt='%m.%d.%Y %I:%M:%S %p',
        level=logging_levels[LOGLEVEL]
    )


root_logger = logging.getLogger()
