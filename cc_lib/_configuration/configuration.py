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

from simple_conf import configuration, section, loadConfig
import logging
import os
import typing

formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s: [%(name)s] %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

sc_logger = logging.getLogger('simple-conf')
sc_logger.addHandler(stream_handler)
sc_logger.setLevel(logging.INFO)

user_dir = os.getenv("CC_LIB_USER_PATH") or os.getcwd()
user_dir = os.path.join(user_dir, "cc-lib")


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
        loop_time: typing.Union[int, float] = 1
        reconn_delay_min: int = 5
        reconn_delay_max: int = 120
        reconn_delay_factor: typing.Union[int, float] = 1.85

    @section
    class auth:
        host: str = None
        path: str = None
        tls: bool = True
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
        colored: bool = False
        rotating_log: bool = False
        rotating_log_backup_count: int = 14

    @section
    class api:
        host: str = None
        hub_endpt: str = None
        device_endpt: str = None
        tls: bool = True
        request_timeout: typing.Union[int, float] = 30
        eventual_consistency_delay: typing.Union[int, float] = 2

    @section
    class device:
        id_prefix: str = None


cc_conf = ConnectorConf(conf_file='connector.conf', user_path=user_dir, ext_aft_crt=True, load=False)


def initConnectorConf() -> None:
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    loadConfig(cc_conf)
