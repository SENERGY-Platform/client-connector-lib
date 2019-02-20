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
from queue import Queue


logger = root_logger.getChild(__name__.split('.', 1)[-1])


class MQTTClient():
    def __init__(self, id: str, host: str, port: int, keepalive: int, msg_queue: Queue): #store keepalive in conf
        self.__id = id
        self.__host = host
        self.__port = port
        self.__msg_queue = msg_queue
        self.__keepalive = keepalive

        self.__mqtt = Client(client_id=self.__id, clean_session=True, userdata=None)
        self.__mqtt.enable_logger(logger)
        self.__mqtt.on_connect = self.__connectClbk
        self.__mqtt.on_disconnect = self.__disconnectClbk
        self.__mqtt.on_message = self.__messageClbk
        self.__mqtt.on_publish = self.__publishClbk
        self.__mqtt.on_subscribe = self.__subscribeClbk
        self.__mqtt.on_unsubscribe = self.__unsubscribeClbk

    def connect(self):
        self.__mqtt.connect_async(host=self.__host, port=self.__port, keepalive=self.__keepalive)
        self.__mqtt.loop_start()

    def disconnect(self):
        self.__mqtt.disconnect()

    def subscribe(self, topic: str, qos: int = 0):
        self.__mqtt.subscribe(topic=topic, qos=qos)

    def unsubscribe(self, topic: str) -> tuple:
        return self.__mqtt.unsubscribe(topic=topic)

    def publish(self, topic: str, payload: str = None, qos: int = 0, retain: bool = False, block: bool = False) -> MQTTMessageInfo:
        msg_info = self.__mqtt.publish(topic=topic, payload=payload, qos=qos, retain=retain)
        if block:
            msg_info.wait_for_publish()
        return msg_info

    def __connectClbk(self, client: Client, userdata, flags: dict, rc: int):
        pass
        # called when the broker responds to our connection
        #   request.
        #   flags is a dict that contains response flags from the broker:
        #     flags['session present'] - this flag is useful for clients that are
        #         using clean session set to 0 only. If a client with clean
        #         session=0, that reconnects to a broker that it has previously
        #         connected to, this flag indicates whether the broker still has the
        #         session information for the client. If 1, the session still exists.
        #   The value of rc determines success or not:
        #     0: Connection successful
        #     1: Connection refused - incorrect protocol version
        #     2: Connection refused - invalid client identifier
        #     3: Connection refused - server unavailable
        #     4: Connection refused - bad username or password
        #     5: Connection refused - not authorised
        #     6-255: Currently unused.

    def __disconnectClbk(self, client: Client, userdata, rc: int):
        client.reinitialise(client_id=client._client_id, clean_session=True, userdata=None)
        # called when the client disconnects from the broker.
        #   The rc parameter indicates the disconnection state. If MQTT_ERR_SUCCESS
        #   (0), the callback was called in response to a disconnect() call. If any
        #   other value the disconnection was unexpected, such as might be caused by
        #   a network error.

    def __messageClbk(self, client: Client, userdata, message: MQTTMessage):
        pass
        # called when a message has been received on a
        #   topic that the client subscribes to. The message variable is a
        #   MQTTMessage that describes all of the message parameters.

    def __publishClbk(self, client: Client, userdata, mid: int):
        pass
        # called when a message that was to be sent using the
        #   publish() call has completed transmission to the broker. For messages
        #   with QoS levels 1 and 2, this means that the appropriate handshakes have
        #   completed. For QoS 0, this simply means that the message has left the
        #   client. The mid variable matches the mid variable returned from the
        #   corresponding publish() call, to allow outgoing messages to be tracked.
        #   This callback is important because even if the publish() call returns
        #   success, it does not always mean that the message has been sent.

    def __subscribeClbk(self, client: Client, userdata, mid: int, granted_qos: int):
        pass
        # called when the broker responds to a
        #   subscribe request. The mid variable matches the mid variable returned
        #   from the corresponding subscribe() call. The granted_qos variable is a
        #   list of integers that give the QoS level the broker has granted for each
        #   of the different subscription requests.
        #

    def __unsubscribeClbk(self, client: Client, userdata, mid: int):
        pass
        # called when the broker responds to an unsubscribe
        #   request. The mid variable matches the mid variable returned from the
        #   corresponding unsubscribe() call.

