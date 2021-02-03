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

import logging
import os
import typing


file_conf_manager = os.getenv("CC_LIB_CONF_MANAGER") == "file"

if file_conf_manager:
    import simple_conf as conf_manager
else:
    import simple_env_var as conf_manager


formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s: [%(name)s] %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

if file_conf_manager:
    sc_logger = logging.getLogger('simple-conf')
else:
    sc_logger = logging.getLogger('simple-env-var')
sc_logger.addHandler(stream_handler)
sc_logger.setLevel(logging.INFO)

user_dir = os.getenv("CC_LIB_USER_PATH") or os.getcwd()


@conf_manager.configuration
class CC_Lib:

    @conf_manager.section
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

    # @conf_manager.section
    # class hub:
    #     name: str = None
    #     id: str = None

    @conf_manager.section
    class logger:
        level: str = 'info'
        colored: bool = False
        rotating_log: bool = False
        rotating_log_backup_count: int = 14

    @conf_manager.section
    class api:
        hub_endpt: str = None
        device_endpt: str = None
        auth_endpt: str = None
        request_timeout: typing.Union[int, float] = 30
        eventual_consistency_delay: typing.Union[int, float] = 2

    #
    # @conf_manager.section
    # class fog:
    #     enable: bool = False


if file_conf_manager:
    cc_conf = CC_Lib(conf_file='cc_lib.conf', user_path=user_dir, ext_aft_crt=True, load=False)
else:
    cc_conf = CC_Lib(load=False)


def initConnectorConf() -> None:
    conf_manager.loadConfig(cc_conf)
