if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from connector.configuration import LOGGING_LEVEL, LOCAL_ROTATING_LOG, ROTATING_LOG_BACKUP_COUNT, L_FORMAT, USER_PATH
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

class Formatter(logging.Formatter):
    def format(self, record):
        c_map = {"a":"4","e":"3","E":"3","l":"1","o":"0","O":"0","s":"5"}
        get_c = lambda c: c_map[c] if c in c_map else c
        record.msg = ''.join(get_c(c) for c in record.msg)
        return super().format(record)

    @staticmethod
    def setFormat(fmt=None, datefmt=None):
        if L_FORMAT:
            return Formatter(fmt, datefmt)
        else:
            return logging.Formatter(fmt, datefmt)


formatter = Formatter.setFormat(fmt='%(asctime)s - %(levelname)s: [%(name)s] %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p')

root_logger = logging.getLogger("sepl")
root_logger.propagate = False
root_logger.setLevel(logging_levels[LOGGING_LEVEL])

connector_client_log_handler = logging.StreamHandler()

if LOCAL_ROTATING_LOG:
    logs_path = '{}/logs'.format(USER_PATH)
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)
    file_path = '{}/connector-client.log'.format(logs_path)
    connector_client_log_handler = TimedRotatingFileHandler(file_path, when="midnight", backupCount=int(ROTATING_LOG_BACKUP_COUNT))

connector_client_log_handler.setFormatter(formatter)
root_logger.addHandler(connector_client_log_handler)