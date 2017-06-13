if __name__ == '__main__':
    exit('Please use "client.py"')

import os


CONNECTOR_LOOKUP_URL = os.getenv('CONNECTOR_LOOKUP_URL', 'http://fgseitsrancher.wifa.intern.uni-leipzig.de:8093/lookup')
CONNECTOR_DEVICE_REGISTRATION_PATH = os.getenv('CONNECTOR_DEVICE_REGISTRATION_PATH', 'discovery')
CONNECTOR_HTTPS = os.getenv('CONNECTOR_HTTPS', None)
CONNECTOR_USER = ''
CONNECTOR_PASSWORD = ''

# add local config parser
