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
    'ConnectError'
)

from ...._util import get_logger
import paho.mqtt.client
import threading
import typing
import ssl


logger = get_logger(__name__.split('.', 1)[-1].replace("_", ""))


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
        self.__mqtt = paho.mqtt.client.Client(client_id=client_id, clean_session=True)
        self.__setup_mqtt()
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None

    def __setup_mqtt(self):
        self.__mqtt.enable_logger(logger)
        if self.__tls:
            self.__mqtt.tls_set()
        self.__mqtt.message_retry_set(self.__msg_retry)
        self.__mqtt.on_message = self.__message_clbk
        self.__mqtt.on_publish = self.__publish_clbk
        self.__mqtt.on_subscribe = self.__subscribe_clbk
        self.__mqtt.on_unsubscribe = self.__unsubscribe_clbk
        self.__mqtt.on_connect = self.__connect_clbk

    def __clean_events(self):
        for event in self.__events.values():
            event.exception = NotConnectedError("aborted due to disconnect")
            event.usr_method(event)
            event.set()
        self.__events.clear()

    def __set_event(self, e_id: typing.Union[int, str], ex: Exception = None) -> bool:
        try:
            event = self.__events[e_id]
            del self.__events[e_id]
            if ex:
                event.exception = ex
            event.usr_method(event)
            event.set()
            return True
        except KeyError:
            return False

    def __loop(self, host: str, port: int):
        try:
            rc = self.__mqtt.connect(host=host, port=port, keepalive=self.__keepalive)
            if rc == paho.mqtt.client.MQTT_ERR_SUCCESS:
                logger.debug("starting loop")
                loop_ex = None
                try:
                    while rc == paho.mqtt.client.MQTT_ERR_SUCCESS:
                        rc = self.__mqtt.loop(timeout=self.__loop_time)
                        if self.__usr_disconn:
                            self.__usr_disconn = False
                            self.__mqtt.disconnect()
                            break
                except OSError as loop_ex:
                    logger.error("socket error - {}".format(loop_ex))
                logger.debug("loop stopped")
                try:
                    event = self.__events["connect_event"]
                    if not event.exception:
                        if loop_ex:
                            event.exception = loop_ex
                        elif not rc == paho.mqtt.client.MQTT_ERR_SUCCESS:
                            event.exception = ConnectError(paho.mqtt.client.error_string(rc).replace(".", "").lower())
                except KeyError:
                    pass
                if not self.__set_event("connect_event"):
                    self.__clean_events()
                    if loop_ex:
                        self.on_disconnect(99, loop_ex)
                    else:
                        # https://github.com/eclipse/paho.mqtt.python/issues/340#issuecomment-447632278
                        self.on_disconnect(
                            rc,
                            "generic error" if rc == 1 else paho.mqtt.client.error_string(rc).replace(".", "").lower()
                        )
            else:
                self.__set_event("connect_event", ConnectError(paho.mqtt.client.error_string(rc).replace(".", "").lower()))
        except ssl.CertificateError as ex:
            self.__set_event("connect_event", ConnectError(ex))
        except (ValueError, TypeError) as ex:
            self.__set_event("connect_event", ConnectError(ex))
        except Exception as ex:
            self.__set_event("connect_event", ConnectError(ex))

    def __connect_clbk(self, client: paho.mqtt.client.Client, userdata: typing.Any, flags: dict, rc: int) -> None:
        if rc > 0:
            try:
                event = self.__events["connect_event"]
                event.exception = ConnectError(paho.mqtt.client.connack_string(rc).replace(".", "").lower())
            except KeyError:
                pass
        else:
            self.__set_event("connect_event")
            self.on_connect()

    def __message_clbk(self, client: paho.mqtt.client.Client, userdata: typing.Any, message) -> None:
        self.on_message(message.payload, message.topic)

    def __publish_clbk(self, client: paho.mqtt.client.Client, userdata: typing.Any, mid: int) -> None:
        self.__set_event(mid)

    def __subscribe_clbk(self, client: paho.mqtt.client.Client, userdata: typing.Any, mid: int, granted_qos: int) -> None:
        if 128 in granted_qos:
            self.__set_event(mid, SubscribeNotAllowedError("subscribe request not allowed"))
        else:
            self.__set_event(mid)

    def __unsubscribe_clbk(self, client: paho.mqtt.client.Client, userdata: typing.Any, mid: int) -> None:
        self.__set_event(mid)

    def connect(self, host: str, port: int, usr: str, pw: str, event_worker) -> None:
        self.__mqtt.username_pw_set(usr, pw)
        self.__events["connect_event"] = event_worker
        self.__loop_thread = threading.Thread(target=self.__loop, name="mqtt-loop", args=(host, port), daemon=True)
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
            if res[0] is paho.mqtt.client.MQTT_ERR_SUCCESS:
                self.__events[res[1]] = event_worker
                logger.debug("request subscribe for '{}'".format(topic))
            elif res[0] == paho.mqtt.client.MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise SubscribeError(paho.mqtt.client.error_string(res[0]).replace(".", "").lower())
        except OSError as ex:
            raise SubscribeError(ex)

    def unsubscribe(self, topic: str, event_worker) -> None:
        try:
            res = self.__mqtt.unsubscribe(topic=topic)
            if res[0] is paho.mqtt.client.MQTT_ERR_SUCCESS:
                self.__events[res[1]] = event_worker
                logger.debug("request unsubscribe for '{}'".format(topic))
            elif res[0] == paho.mqtt.client.MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise UnsubscribeError(paho.mqtt.client.error_string(res[0]).replace(".", "").lower())
        except OSError as ex:
            raise UnsubscribeError(ex)

    def publish(self, topic: str, payload: str, qos: int, event_worker) -> None:
        try:
            msg_info = self.__mqtt.publish(topic=topic, payload=payload, qos=qos, retain=False)
            if msg_info.rc == paho.mqtt.client.MQTT_ERR_SUCCESS:
                if qos > 0:
                    self.__events[msg_info.mid] = event_worker
                else:
                    event_worker.usr_method(event_worker)
                    event_worker.set()
                logger.debug("publish '{}' - (q{}, m{})".format(payload, qos, msg_info.mid))
            elif msg_info.rc == paho.mqtt.client.MQTT_ERR_NO_CONN:
                raise NotConnectedError
            else:
                raise PublishError(paho.mqtt.client.error_string(msg_info.rc).replace(".", "").lower())
        except (ValueError, OSError) as ex:
            raise PublishError(ex)
