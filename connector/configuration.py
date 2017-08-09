if __name__ == '__main__':
    exit('Please use "client.py"')

import os


CONNECTOR_PROTOCOL = os.getenv('CONNECTOR_HTTPS', 'ws')
CONNECTOR_HOST = os.getenv('CONNECTOR_HOST', 'fgseitsrancher.wifa.intern.uni-leipzig.de')
CONNECTOR_PORT = os.getenv('CONNECTOR_PORT', 8092)
CONNECTOR_USER = ''
CONNECTOR_PASSWORD = ''

# add local config parser
