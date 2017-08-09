if __name__ == '__main__':
    exit('Please use "client.py"')

import os


CONNECTOR_PROTOCOL = os.getenv('CONNECTOR_HTTPS', 'ws')
CONNECTOR_HOST = os.getenv('CONNECTOR_HOST', 'fgseitsrancher.wifa.intern.uni-leipzig.de')
CONNECTOR_PORT = os.getenv('CONNECTOR_PORT', 8092)
CONNECTOR_USER = ''
CONNECTOR_PASSWORD = ''

LOGLEVEL = os.getenv('LOGGING_LEVEL', 'info')
LOCAL_ROTATING_LOG = os.getenv('LOCAL_ROTATING_LOG', None)
ROTATING_LOG_BACKUP_COUNT = os.getenv('ROTATING_LOG_BACKUP_COUNT', 7)

# add local config parser
