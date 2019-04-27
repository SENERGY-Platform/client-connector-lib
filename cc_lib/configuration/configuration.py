"""
   Copyright 2019 InfAI (CC SES)

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

from simple_conf import configuration, section, initConfig
from os import getcwd, makedirs
from os.path import exists as path_exists
import logging

formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s: [%(name)s] %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

sc_logger = logging.getLogger('simple-conf')
sc_logger.addHandler(stream_handler)
sc_logger.setLevel(logging.INFO)

user_dir = '{}/cc-lib'.format(getcwd())

@configuration
class ConnectorConf:

    @section
    class connector:
        host: str = None
        port: int = None
        tls: bool = True
        qos: int = "normal"
        msg_retry: int = 5
        keepalive: int = 20
        loop_time: float = 0.2
        reconn_delay_min = 1
        reconn_delay_max = 240
        reconn_delay_factor = 1.75

    @section
    class auth:
        host: str = None
        path: str = None
        id: str = None

    @section
    class credentials:
        user: str = None
        pw: str = None

    @section
    class hub:
        name: str = None
        id: str = None

    @section
    class logger:
        level: str = 'info'
        rotating_log: bool = False
        rotating_log_backup_count: int = 14

    @section
    class api:
        host: str = None
        hub_endpt: str = None
        device_endpt: str = None
        req_timeout: int = 30

    @section
    class device:
        id_prefix: str = None


cc_conf = ConnectorConf(conf_file='connector.conf', user_path=user_dir, ext_aft_crt=True, init=False)


def initConnectorConf() -> None:
    if not path_exists(user_dir):
        makedirs(user_dir)
    initConfig(cc_conf)
