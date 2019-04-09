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

__all__ = ('Client', 'NotConnectedError', 'SubscribeError', 'UnsubscribeError')

from ....logger.logger import _getLibLogger
from paho.mqtt.client import Client as PahoClient
from paho.mqtt.client import error_string, connack_string, MQTTMessage, MQTTMessageInfo, MQTT_ERR_SUCCESS, MQTT_ERR_NO_CONN
from threading import Event
import socket


logger = _getLibLogger(__name__.split('.', 1)[-1])


class MqttClientError(Exception):
    pass


class NotConnectedError(MqttClientError):
    pass


class SubscribeError(MqttClientError):
    pass


class UnsubscribeError(MqttClientError):
    pass


class Client:
    def __init__(self, client_id: str, clean_session=True, userdata=None, reconnect_delay=120):
        self.__mqtt = PahoClient(client_id=client_id, clean_session=clean_session, userdata=userdata)
        self.__mqtt.enable_logger(logger)
        self.__mqtt.reconnect_delay_set(min_delay=1, max_delay=reconnect_delay)
        self.__mqtt.on_connect = self.__connectClbk
        self.__mqtt.on_disconnect = self.__disconnectClbk
        self.__mqtt.on_message = self.__messageClbk
        self.__mqtt.on_publish = self.__publishClbk
        self.__mqtt.on_subscribe = self.__subscribeClbk
        self.__mqtt.on_unsubscribe = self.__unsubscribeClbk
        self.__connect_event = Event()
        self.__events = dict()

    def connect(self, host, port, usr, pw, tls=True, keepalive=15):
        self.__connect_event.clear()
        if tls:
            self.__mqtt.tls_set()
        self.__mqtt.username_pw_set(usr, pw)
        self.__mqtt.connect_async(host=host, port=port, keepalive=keepalive)
        self.__mqtt.loop_start()
        self.__connect_event.wait()

    def disconnect(self):
        self.__mqtt.disconnect()
        self.__mqtt.loop_stop()

    def subscribe(self, topic: str, qos: int = 1, timeout=30):
        try:
            res = self.__mqtt.subscribe(topic=topic, qos=qos)
            if res[0] == MQTT_ERR_SUCCESS:
                event = Event()
                self.__events[res[1]] = event
                if not event.wait(timeout=timeout):
                    logger.error("subscribe request for '{}' failed - timeout".format(topic))
                    del self.__events[res[1]]
                    raise SubscribeError
                del self.__events[res[1]]
                logger.debug("subscribe request for '{}' successful".format(topic, res[1]))
            if res[0] == MQTT_ERR_NO_CONN:
                logger.error("subscribe request for '{}' failed - not connected".format(topic))
                raise NotConnectedError
        except socket.error as ex:
            logger.error("subscribe request for '{}' failed - {}".format(topic, ex))
            raise SubscribeError

    def unsubscribe(self, topic: str, timeout=30):
        try:
            res = self.__mqtt.unsubscribe(topic=topic)
            if res[0] == MQTT_ERR_SUCCESS:
                event = Event()
                self.__events[res[1]] = event
                if not event.wait(timeout=timeout):
                    logger.error("unsubscribe request for '{}' failed - timeout".format(topic))
                    del self.__events[res[1]]
                    raise UnsubscribeError
                del self.__events[res[1]]
                logger.debug("unsubscribe request for '{}' successful".format(topic, res[1]))
            if res[0] == MQTT_ERR_NO_CONN:
                logger.error("unsubscribe request for '{}' failed - not connected".format(topic))
                raise NotConnectedError
        except socket.error as ex:
            logger.error("unsubscribe request for '{}' failed - {}".format(topic, ex))
            raise UnsubscribeError

    def publish(self, topic: str, payload: str = None, qos: int = 0, retain: bool = False):
        msg_info = self.__mqtt.publish(topic=topic, payload=payload, qos=qos, retain=retain)
        msg_info.wait_for_publish()

    def __connectClbk(self, client: PahoClient, userdata, flags: dict, rc: int):
        if rc == 0:
            logger.info(connack_string(rc).replace(".", "").lower())
            logger.debug(flags)
            self.__connect_event.set()
        else:
            logger.error(connack_string(rc))

    def __disconnectClbk(self, client: PahoClient, userdata, rc: int):
        if rc == 0:
            logger.info("disconnected by user")
        else:
            logger.error("unexpected disconnect")

    def __messageClbk(self, client: PahoClient, userdata, message: MQTTMessage):
        pass
        # called when a message has been received on a
        #   topic that the client subscribes to. The message variable is a
        #   MQTTMessage that describes all of the message parameters.

    def __publishClbk(self, client: PahoClient, userdata, mid: int):
        pass
        # called when a message that was to be sent using the
        #   publish() call has completed transmission to the broker. For messages
        #   with QoS levels 1 and 2, this means that the appropriate handshakes have
        #   completed. For QoS 0, this simply means that the message has left the
        #   client. The mid variable matches the mid variable returned from the
        #   corresponding publish() call, to allow outgoing messages to be tracked.
        #   This callback is important because even if the publish() call returns
        #   success, it does not always mean that the message has been sent.

    def __subscribeClbk(self, client: PahoClient, userdata, mid: int, granted_qos: int):
        try:
            event = self.__events[mid]
            event.set()
        except KeyError:
            pass

    def __unsubscribeClbk(self, client: PahoClient, userdata, mid: int):
        try:
            event = self.__events[mid]
            event.set()
        except KeyError:
            pass

