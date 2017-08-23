if __name__ == '__main__':
    exit('Please use "client.py"')

import os, configparser



config = configparser.ConfigParser()

if os.path.isfile('{}/connector.conf'.format(os.getcwd())):
    config.read('{}/connector.conf'.format(os.getcwd()))
elif os.path.isfile('{}/connector_client/connector.conf'.format(os.getcwd())):
    config.read('{}/connector_client/connector.conf'.format(os.getcwd()))
else:
    exit('No config file found')


CONNECTOR_PROTOCOL = os.getenv('CONNECTOR_PROTOCOL', config['CONNECTOR']['protocol'])
CONNECTOR_HOST = os.getenv('CONNECTOR_HOST', config['CONNECTOR']['host'])
CONNECTOR_PORT = os.getenv('CONNECTOR_PORT', config['CONNECTOR']['port'])
CONNECTOR_USER = config['CONNECTOR']['user']
CONNECTOR_PASSWORD = config['CONNECTOR']['password']
