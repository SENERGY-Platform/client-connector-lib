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


import typing
import sevm


class ConnectorConfig(sevm.Config):
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
    request_timeout: typing.Union[int, float] = 30
    eventual_consistency_delay: typing.Union[int, float] = 2


class ApiConfig(sevm.Config):
    hub_endpt: str = None
    device_endpt: str = None
    auth_endpt: str = None
    event_pub_topic: str = "event/{device_id}/{service_id}"
    command_sub_topic: str = "command/{device_id}/+"
    command_response_pub_topic: str = "response/{device_id}/{service_id}"
    fog_processes_sub_topic: str = "processes/{hub_id}/cmd/#"
    fog_processes_pub_topic: str = "processes/{hub_id}/state/{sub_topic}"
    client_error_pub_topic: str = "error"
    device_error_pub_topic: str = "error/device/{device_id}"
    command_error_pub_topic: str = "error/command/{correlation_id}"


class RouterConfig(sevm.Config):
    command_sub_topic_identifier: str = "command"
    fog_processes_sub_topic_identifier: str = "processes"


class Credentials(sevm.Config):
    user: str = None
    pw: str = None
    client_id: str = None


class Config(sevm.Config):
    connector = ConnectorConfig
    api = ApiConfig
    router = RouterConfig
    credentials = Credentials
    device_attribute_origin: str = "local-cc"


cc_conf = Config(prefix="CC_LIB_")
