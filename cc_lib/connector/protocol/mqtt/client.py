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

__all__ = ('Client', 'NotConnectedError', 'SubscribeError', 'UnsubscribeError', 'qos_map')

from ....logger.logger import _getLibLogger
from paho.mqtt.client import Client as PahoClient
from paho.mqtt.client import error_string, connack_string, MQTTMessage, MQTTMessageInfo, MQTT_ERR_SUCCESS, MQTT_ERR_NO_CONN
from threading import Event
from typing import Any
from socket import error as SocketError


logger = _getLibLogger(__name__.split('.', 1)[-1])


qos_map = {
    "low": 0,
    "normal": 1,
    "high": 2
}


class MqttClientError(Exception):
    pass


class NotConnectedError(MqttClientError):
    pass


class SubscribeError(MqttClientError):
    pass


class UnsubscribeError(MqttClientError):
    pass


class PublishError(MqttClientError):
    pass


class Client:
    def __init__(self, client_id: str, reconnect_delay: int, msg_retry: int):
        self.__mqtt = PahoClient(client_id=client_id, clean_session=True)
        self.__mqtt.enable_logger(logger)
        self.__mqtt.reconnect_delay_set(min_delay=1, max_delay=reconnect_delay)
        self.__mqtt.message_retry_set(msg_retry)
        self.__mqtt.on_connect = self.__connectClbk
        self.__mqtt.on_disconnect = self.__disconnectClbk
        self.__mqtt.on_message = self.__messageClbk
        self.__mqtt.on_publish = self.__publishClbk
        self.__mqtt.on_subscribe = self.__subscribeClbk
        self.__mqtt.on_unsubscribe = self.__unsubscribeClbk
        self.__events = dict()
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None

    def connect(self, host: str, port: int, usr: str, pw: str, tls: bool, keepalive: int) -> None:
        if tls:
            self.__mqtt.tls_set()
        self.__mqtt.username_pw_set(usr, pw)
        self.__mqtt.connect_async(host=host, port=port, keepalive=keepalive)
        self.__mqtt.loop_start()

    def disconnect(self) -> None:
        self.__mqtt.disconnect()
        self.__mqtt.loop_stop()

    def subscribe(self, topic: str, qos: int, timeout: int) -> None:
        try:
            res = self.__mqtt.subscribe(topic=topic, qos=qos)
            if res[0] == MQTT_ERR_SUCCESS:
                event = Event()
                self.__events[res[1]] = event
                if not event.wait(timeout=timeout):
                    del self.__events[res[1]]
                    raise SubscribeError("subscribe acknowledgment timeout")
                del self.__events[res[1]]
                logger.debug("subscribe request for '{}' successful".format(topic))
            elif res[0] == MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise SubscribeError(error_string(res[0]).replace(".", "").lower())
        except SocketError as ex:
            raise SubscribeError(ex)

    def unsubscribe(self, topic: str, timeout: int) -> None:
        try:
            res = self.__mqtt.unsubscribe(topic=topic)
            if res[0] == MQTT_ERR_SUCCESS:
                event = Event()
                self.__events[res[1]] = event
                if not event.wait(timeout=timeout):
                    del self.__events[res[1]]
                    raise UnsubscribeError("unsubscribe acknowledgment timeout")
                del self.__events[res[1]]
                logger.debug("unsubscribe request for '{}' successful".format(topic))
            elif res[0] == MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise UnsubscribeError(error_string(res[0]).replace(".", "").lower())
        except SocketError as ex:
            raise UnsubscribeError(ex)

    def publish(self, topic: str, payload: str, qos: int, timeout: int) -> None:
        try:
            msg_info = self.__mqtt.publish(topic=topic, payload=payload, qos=qos, retain=False)
            if msg_info.rc == MQTT_ERR_SUCCESS:
                event = Event()
                self.__events[msg_info.mid] = event
                if not event.wait(timeout=timeout):
                    del self.__events[msg_info.mid]
                    raise PublishError("publish acknowledgment timeout")
                del self.__events[msg_info.mid]
                logger.debug("published '{}' on '{}'".format(payload, topic))
            elif msg_info.rc == MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise PublishError(error_string(msg_info.rc).replace(".", "").lower())
        except (ValueError, SocketError) as ex:
            raise PublishError(ex)

    def __connectClbk(self, client: PahoClient, userdata: Any, flags: dict, rc: int) -> None:
        if rc == 0:
            logger.debug(connack_string(rc).replace(".", "").lower())
            logger.debug(flags)
            if self.on_connect:
                self.on_connect()
        else:
            logger.error(connack_string(rc).replace(".", "").lower())

    def __disconnectClbk(self, client: PahoClient, userdata: Any, rc: int) -> None:
        if self.on_disconnect:
            self.on_disconnect(rc)

    def __messageClbk(self, client: PahoClient, userdata: Any, message: MQTTMessage) -> None:
        self.on_message(message.payload, message.topic)

    def __publishClbk(self, client: PahoClient, userdata: Any, mid: int) -> None:
        try:
            event = self.__events[mid]
            event.set()
        except KeyError:
            pass

    def __subscribeClbk(self, client: PahoClient, userdata: Any, mid: int, granted_qos: int) -> None:
        try:
            event = self.__events[mid]
            event.set()
        except KeyError:
            pass

    def __unsubscribeClbk(self, client: PahoClient, userdata: Any, mid: int) -> None:
        try:
            event = self.__events[mid]
            event.set()
        except KeyError:
            pass
