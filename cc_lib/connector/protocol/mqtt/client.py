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

__all__ = (
    'Client',
    'MqttClientError',
    'NotConnectedError',
    'SubscribeError',
    'UnsubscribeError',
    'PublishError',
    'SubscribeNotAllowedError',
    'ConnectError',
    'qos_map'
)

from ....logger.logger import _getLibLogger
from paho.mqtt.client import Client as PahoClient
from paho.mqtt.client import MQTT_ERR_SUCCESS, MQTT_ERR_NO_CONN, connack_string, error_string
from threading import Thread
from typing import Any, Union
from ssl import CertificateError


logger = _getLibLogger(__name__.split('.', 1)[-1])


qos_map = {
    "low": 0,
    "normal": 1,
    "high": 2
}


class MqttClientError(Exception):
    pass


class ConnectError(MqttClientError):
    pass


class NotConnectedError(MqttClientError):
    pass


class SubscribeError(MqttClientError):
    pass


class SubscribeNotAllowedError(SubscribeError):
    pass


class UnsubscribeError(MqttClientError):
    pass


class PublishError(MqttClientError):
    pass


class Client:
    def __init__(self, client_id: str, msg_retry: int, keepalive: int, loop_time: float, tls: bool):
        if not loop_time > 0.0:
            raise MqttClientError("loop time must be larger than 0")
        if keepalive <= loop_time:
            raise MqttClientError("keepalive must be larger than loop time")
        if msg_retry <= loop_time:
            raise MqttClientError("msg retry delay must be larger than loop time")
        self.__msg_retry = msg_retry
        self.__keepalive = keepalive
        self.__loop_time = loop_time
        self.__tls = tls
        self.__events = dict()
        self.__loop_thread = None
        self.__usr_disconn = False
        self.__mqtt = PahoClient(client_id=client_id, clean_session=True)
        self.__setup_mqtt()
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None

    def __setup_mqtt(self):
        self.__mqtt.enable_logger(logger)
        if self.__tls:
            self.__mqtt.tls_set()
        self.__mqtt.message_retry_set(self.__msg_retry)
        self.__mqtt.on_message = self.__messageClbk
        self.__mqtt.on_publish = self.__publishClbk
        self.__mqtt.on_subscribe = self.__subscribeClbk
        self.__mqtt.on_unsubscribe = self.__unsubscribeClbk
        self.__mqtt.on_connect = self.__connectClbk

    def __cleanEvents(self):
        for event in self.__events.values():
            event.exception = NotConnectedError("aborted due to disconnect")
            event.usr_method()
            event.set()
        self.__events.clear()

    def __setEvent(self, e_id: Union[int, str], ex: Exception = None) -> bool:
        try:
            event = self.__events[e_id]
            del self.__events[e_id]
            if ex:
                event.exception = ex
            event.usr_method()
            event.set()
            return True
        except KeyError:
            return False

    def __loop(self, host: str, port: int):
        try:
            rc = self.__mqtt.connect(host=host, port=port, keepalive=self.__keepalive)
            if rc == MQTT_ERR_SUCCESS:
                logger.debug("starting loop")
                try:
                    while rc == MQTT_ERR_SUCCESS:
                        rc = self.__mqtt.loop(timeout=self.__loop_time)
                        if self.__usr_disconn:
                            self.__usr_disconn = False
                            self.__mqtt.disconnect()
                            break
                except OSError as ex:
                    logger.error("socket error - {}".format(ex))
                logger.debug("loop stopped")
                if not rc == MQTT_ERR_SUCCESS:
                    connect_attempt = self.__setEvent("connect_event", ConnectError(error_string(rc).replace(".", "").lower()))
                    if not connect_attempt:
                        logger.error(error_string(rc).replace(".", "").lower())
                else:
                    connect_attempt = self.__setEvent("connect_event")
                if not connect_attempt:
                    self.__cleanEvents()
                    self.on_disconnect(rc)
            else:
                # logger.error(error_string(rc).replace(".", "").lower())
                self.__setEvent("connect_event", ConnectError(error_string(rc).replace(".", "").lower()))
        except CertificateError as ex:
            # logger.error("certificate error - {}".format(ex))
            self.__setEvent("connect_event", ConnectError(ex))
        except (ValueError, TypeError) as ex:
            # logger.error("host or port error - {}".format(ex))
            self.__setEvent("connect_event", ConnectError(ex))
        except OSError as ex:
            # logger.error("socket error - {}".format(ex))
            self.__setEvent("connect_event", ConnectError(ex))

    def __connectClbk(self, client: PahoClient, userdata: Any, flags: dict, rc: int) -> None:
        if rc > 0:
            self.__setEvent("connect_event", ConnectError(connack_string(rc).replace(".", "").lower()))
        else:
            self.__setEvent("connect_event")
            self.on_connect()

    def __messageClbk(self, client: PahoClient, userdata: Any, message) -> None:
        self.on_message(message.payload, message.topic)

    def __publishClbk(self, client: PahoClient, userdata: Any, mid: int) -> None:
        self.__setEvent(mid)

    def __subscribeClbk(self, client: PahoClient, userdata: Any, mid: int, granted_qos: int) -> None:
        if 128 in granted_qos:
            self.__setEvent(mid, SubscribeNotAllowedError("subscribe request not allowed"))
        else:
            self.__setEvent(mid)

    def __unsubscribeClbk(self, client: PahoClient, userdata: Any, mid: int) -> None:
        self.__setEvent(mid)

    def connect(self, host: str, port: int, usr: str, pw: str, event_worker) -> None:
        self.__mqtt.username_pw_set(usr, pw)
        self.__events["connect_event"] = event_worker
        self.__loop_thread = Thread(target=self.__loop, name="mqtt-loop", args=(host, port), daemon=True)
        self.__loop_thread.start()

    def reset(self, client_id: str):
        self.__mqtt.reinitialise(client_id=client_id, clean_session=True)
        self.__setup_mqtt()

    def disconnect(self) -> None:
        if self.__mqtt._sock is None:
            raise NotConnectedError
        self.__usr_disconn = True

    def subscribe(self, topic: str, qos: int, event_worker) -> None:
        try:
            res = self.__mqtt.subscribe(topic=topic, qos=qos)
            if res[0] is MQTT_ERR_SUCCESS:
                self.__events[res[1]] = event_worker
                logger.debug("request subscribe for '{}'".format(topic))
            elif res[0] == MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise SubscribeError(error_string(res[0]).replace(".", "").lower())
        except OSError as ex:
            raise SubscribeError(ex)

    def unsubscribe(self, topic: str, event_worker) -> None:
        try:
            res = self.__mqtt.unsubscribe(topic=topic)
            if res[0] is MQTT_ERR_SUCCESS:
                self.__events[res[1]] = event_worker
                logger.debug("request unsubscribe for '{}'".format(topic))
            elif res[0] == MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise UnsubscribeError(error_string(res[0]).replace(".", "").lower())
        except OSError as ex:
            raise UnsubscribeError(ex)

    def publish(self, topic: str, payload: str, qos: int, event_worker) -> None:
        try:
            msg_info = self.__mqtt.publish(topic=topic, payload=payload, qos=qos, retain=False)
            if msg_info.rc == MQTT_ERR_SUCCESS:
                if qos > 0:
                    self.__events[msg_info.mid] = event_worker
                else:
                    event_worker.usr_method()
                    event_worker.set()
                logger.debug("publish '{}' - (q{}, m{})".format(payload, qos, msg_info.mid))
            elif msg_info.rc == MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise PublishError(error_string(msg_info.rc).replace(".", "").lower())
        except (ValueError, OSError) as ex:
            raise PublishError(ex)
