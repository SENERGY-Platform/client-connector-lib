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

__all__ = ("cc_conf", )


import os
import typing


file_conf_manager = os.getenv("CC_LIB_CONF_MANAGER") == "file"

if file_conf_manager:
    import simple_conf as conf_manager
else:
    import simple_env_var as conf_manager

user_dir = os.getenv("CC_LIB_USER_PATH") or os.getcwd()


@conf_manager.configuration
class CC_Lib:

    @conf_manager.section
    class connector:
        host: str = None
        port: int = None
        tls: bool = True
        qos: int = 2
        msg_retry: int = 5
        keepalive: int = 20
        clean_session: bool = True
        loop_time: typing.Union[int, float] = 1
        reconn_delay_min: int = 5
        reconn_delay_max: int = 120
        reconn_delay_factor: typing.Union[int, float] = 1.85
        low_level_logger: bool = False

    @conf_manager.section
    class api:
        hub_endpt: str = None
        device_endpt: str = None
        auth_endpt: str = None
        request_timeout: typing.Union[int, float] = 30
        eventual_consistency_delay: typing.Union[int, float] = 2


if file_conf_manager:
    cc_conf = CC_Lib(conf_file='cc_lib.conf', user_path=user_dir, ext_aft_crt=True)
else:
    cc_conf = CC_Lib()
