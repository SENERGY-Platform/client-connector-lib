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

try:
    from ...logger import root_logger
    from paho.mqtt.client import Client, error_string, connack_string, MQTTMessage, MQTTMessageInfo
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))


logger = root_logger.getChild(__name__.split('.', 1)[-1])

logger.info(123)