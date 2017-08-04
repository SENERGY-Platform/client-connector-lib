if __name__ == '__main__':
    exit('Please use "client.py"')

import logging, os


LOGLEVEL = os.getenv('LOGGING_LEVEL', 'debug')

# logging level mapper
logging_levels = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'debug': logging.DEBUG
}

# format log output
logging.basicConfig(
    #format='%(asctime)s - %(threadName)s - %(levelname)s: [%(name)s] %(message)s',
    format='%(asctime)s - %(levelname)s: [%(name)s] %(message)s',
    datefmt='%m.%d.%Y %I:%M:%S %p',
    level=logging_levels[LOGLEVEL]
)

root_logger = logging.getLogger()
