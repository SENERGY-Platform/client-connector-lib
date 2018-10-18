"""
   Copyright 2018 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os, inspect, configparser

init_path = '{}/__init__.py'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))

def read_version():
    values = dict()
    with open(init_path, 'r') as init_file:
        exec(init_file.read(), values)
    return values.get('__version__')

USER_PATH = '{}/sepl-connector-client'.format(os.getcwd())

if not os.path.exists(USER_PATH):
    os.makedirs(USER_PATH)

config = configparser.ConfigParser()

conf_file_path = '{}/client.conf'.format(USER_PATH)

if not os.path.isfile(conf_file_path):
    print('No config file found')
    config['CONNECTOR'] = {
        'encryption': 'no',
        'host': 'connector.sepl.infai.org',
        'port': '8093',
        'user': '',
        'password': '',
        'gid': ''
    }
    config['LOGGER'] = {
        'level': 'info',
        'rotating_log': 'no',
        'rotating_log_backup_count': 14
    }
    with open(conf_file_path, 'w') as conf_file:
        config.write(conf_file)
    exit("Created blank config file at '{}'".format(USER_PATH))


try:
    config.read(conf_file_path)
except Exception as ex:
    exit(ex)


def writeConf(section, option, value):
    config.set(section=section, option=option, value=value)
    try:
        with open(conf_file_path, 'w') as conf_file:
            config.write(conf_file)
    except Exception as ex:
        print(ex)


protocol_map = {
    'yes': 'wss',
    'no': 'ws'
}


CONNECTOR_WS_ENCRYPTION = protocol_map[config['CONNECTOR']['encryption']]
CONNECTOR_WS_HOST = config['CONNECTOR']['host']
CONNECTOR_WS_PORT = config['CONNECTOR']['port']
CONNECTOR_USER = config['CONNECTOR']['user']
CONNECTOR_PASSWORD = config['CONNECTOR']['password']
GATEWAY_ID = config['CONNECTOR']['gid']
LOGGING_LEVEL = os.getenv('CONNECTOR_CLIENT_LOG_LEVEL', config['LOGGER']['level'])
LOCAL_ROTATING_LOG = config['LOGGER'].getboolean('rotating_log')
ROTATING_LOG_BACKUP_COUNT = config['LOGGER']['rotating_log_backup_count']
L_FORMAT = os.environ.get('L_FORMAT')
VERSION = read_version()
