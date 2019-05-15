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

__all__ = ("Client", )

from ..configuration.configuration import cc_conf, initConnectorConf
from ..logger.logger import getLogger, initLogging
from ..device import Device
from .message import Envelope, Message
from .exception import *
from .singleton import Singleton
from .auth import OpenIdClient, NoTokenError
from .protocol import http, mqtt
from .asynchron import Future, ThreadWorker, EventWorker
from cc_lib import __version__ as VERSION
from typing import Callable, Union, Any, Tuple, List, Optional
from getpass import getuser
from math import ceil, log10
from datetime import datetime
from hashlib import md5, sha1
from base64 import urlsafe_b64encode
from time import time, sleep
from queue import Queue
from queue import Full as QueueFull
from queue import Empty as QueueEmpty
from threading import Thread, Event, Lock, RLock, current_thread
from json import loads as jsonLoads
from json import dumps as jsonDumps
from json import JSONDecodeError


logger = getLogger(__name__.rsplit(".", 1)[-1])


class _SendHandler:
    event = "event"
    response = "response"


class Client(metaclass=Singleton):
    """
    Client class for client-connector projects.
    To avoid multiple instantiations the Client class implements the singleton pattern.
    """

    def __init__(self):
        """
        Create a Client instance. Set device manager, initiate configuration and library logging facility.
        """
        initConnectorConf()
        initLogging()
        logger.info(20 * "-" + " client-connector-lib v{} ".format(VERSION) + 20 * "-")
        if not cc_conf.device.id_prefix:
            usr_time_str = '{}{}'.format(
                md5(bytes(cc_conf.credentials.user, 'UTF-8')).hexdigest(),
                time()
            )
            cc_conf.device.id_prefix = urlsafe_b64encode(
                md5(usr_time_str.encode()).digest()
            ).decode().rstrip('=')
        self.__auth = OpenIdClient(
            "https://{}/{}".format(cc_conf.auth.host, cc_conf.auth.path),
            cc_conf.credentials.user,
            cc_conf.credentials.pw,
            cc_conf.auth.id
        )
        self.__comm: mqtt.Client = None
        self.__connected_flag = False
        self.__connect_lock = Lock()
        self.__reconnect_flag = False
        self.__cmd_queue = Queue()
        self.__workers = list()
        self.__hub_sync_event = Event()
        self.__hub_sync_event.set()
        self.__hub_sync_lock = Lock()
        self.__hub_init = False
        self.__connect_clbk = None
        self.__disconnect_clbk = None
        self.__set_clbk_lock = RLock()

    # ------------- internal methods ------------- #

    def __initHub(self) -> None:
        try:
            logger.info("initializing hub ...")
            access_token = self.__auth.getAccessToken()
            if not cc_conf.hub.id:
                logger.info("creating new hub ...")
                hub_name = cc_conf.hub.name
                if not hub_name:
                    logger.info("generating hub name ...")
                    hub_name = "{}-{}".format(getuser(), datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
                req = http.Request(
                    url="https://{}/{}".format(cc_conf.api.host, cc_conf.api.hub_endpt),
                    method=http.Method.POST,
                    body={
                        "id": None,
                        "name": hub_name,
                        "hash": None,
                        "devices": list()
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.api.request_timeout
                )
                resp = req.send()
                if not resp.status == 200:
                    logger.error("initializing hub failed - {} {}".format(resp.status, resp.body))
                    raise HubInitializationError
                hub = jsonLoads(resp.body)
                cc_conf.hub.id = hub["id"]
                if not cc_conf.hub.name:
                    cc_conf.hub.name = hub_name
                self.__hub_init = True
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                logger.info("initializing hub successful")
            else:
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                req = http.Request(
                    url="https://{}/{}/{}".format(
                        cc_conf.api.host,
                        cc_conf.api.hub_endpt,
                        http.urlEncode(cc_conf.hub.id)
                    ),
                    method=http.Method.HEAD,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.api.request_timeout
                )
                resp = req.send()
                if resp.status == 200:
                    self.__hub_init = True
                    logger.info("initializing hub successful")
                elif resp.status == 404:
                    logger.error("initializing hub failed - hub not found on platform")
                    cc_conf.hub.id = None
                    raise HubNotFoundError
                else:
                    logger.error("initializing hub failed - {} {}".format(resp.status, resp.body))
                    raise HubInitializationError
        except NoTokenError:
            logger.error("initializing hub failed - could not retrieve access token")
            raise HubInitializationError
        except (http.SocketTimeout, http.URLError) as ex:
            logger.error("initializing hub failed - {}".format(ex))
            raise HubInitializationError
        except JSONDecodeError as ex:
            logger.error("initializing hub failed - could not decode response - {}".format(ex))
            raise HubInitializationError
        except KeyError as ex:
            logger.error("initializing hub failed - malformed response - missing key {}".format(ex))
            raise HubInitializationError

    def __syncHub(self, devices: List[Device]) -> None:
        self.__hub_sync_lock.acquire()
        if not self.__hub_init:
            self.__hub_sync_lock.release()
            logger.error("hub not initialized - synchronizing hub not possible")
            raise HubNotInitializedError
        try:
            try:
                self.__hub_sync_event.clear()
                logger.info("synchronizing hub ...")
                if self.__workers:
                    logger.info("synchronizing hub - waiting for running tasks: {}".format(len(self.__workers)))
                    for worker in self.__workers:
                        worker.join()
                        logger.debug("synchronizing hub - task '{}' finished".format(worker.name))
                    self.__workers.clear()
                device_ids = tuple(__class__.__prefixDeviceID(device.id) for device in devices)
                devices_hash = __class__.__hashDevices(devices)
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                logger.debug("devices {}".format(device_ids))
                logger.debug("hash '{}'".format(devices_hash))
                access_token = self.__auth.getAccessToken()
                req = http.Request(
                    url="https://{}/{}/{}".format(
                        cc_conf.api.host,
                        cc_conf.api.hub_endpt,
                        http.urlEncode(cc_conf.hub.id)
                    ),
                    method=http.Method.GET,
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.api.request_timeout
                )
                resp = req.send()
                if resp.status == 200:
                    hub = jsonLoads(resp.body)
                    if not hub["name"] == cc_conf.hub.name:
                        logger.warning(
                            "synchronizing hub - local name '{}' differs from remote name '{}'".format(
                                cc_conf.hub.name,
                                hub["name"]
                            )
                        )
                        logger.info("synchronizing hub - setting hub name to '{}'".format(hub["name"]))
                        cc_conf.hub.name = hub["name"]
                    if not hub["hash"] == devices_hash:
                        logger.debug("synchronizing hub - local hash differs from remote hash")
                        logger.info("synchronizing hub - updating devices ...")
                        req = http.Request(
                            url="https://{}/{}/{}".format(
                                cc_conf.api.host,
                                cc_conf.api.hub_endpt,
                                http.urlEncode(cc_conf.hub.id)
                            ),
                            method=http.Method.PUT,
                            body={
                                "id": cc_conf.hub.id,
                                "name": cc_conf.hub.name,
                                "hash": devices_hash,
                                "devices": device_ids
                            },
                            content_type=http.ContentType.json,
                            headers={"Authorization": "Bearer {}".format(access_token)},
                            timeout=cc_conf.api.request_timeout
                        )
                        resp = req.send()
                        if resp.status == 200:
                            logger.info("synchronizing hub successful")
                        elif resp.status == 400:
                            logger.error(
                                "synchronizing hub failed - could not update devices"
                            )
                            raise HubSyncDeviceError
                        elif resp.status == 404:
                            logger.error("synchronizing hub failed - hub not found on platform")
                            cc_conf.hub.id = None
                            raise HubNotFoundError
                        else:
                            logger.error(
                                "synchronizing hub failed - {} {}".format(resp.status, resp.body)
                            )
                            raise HubSyncError
                elif resp.status == 404:
                    logger.error("synchronizing hub failed - hub not found on platform")
                    cc_conf.hub.id = None
                    raise HubNotFoundError
                else:
                    logger.error("synchronizing hub failed - {} {}".format(resp.status, resp.body))
                    raise HubSyncError
            except NoTokenError:
                logger.error("synchronizing hub failed - could not retrieve access token")
                raise HubSyncError
            except (http.SocketTimeout, http.URLError) as ex:
                logger.error("synchronizing hub failed - {}".format(ex))
                raise HubSyncError
            except JSONDecodeError as ex:
                logger.error("synchronizing hub failed - could not decode response - {}".format(ex))
                raise HubSyncError
            except KeyError as ex:
                logger.error("synchronizing hub failed - malformed response - missing key {}".format(ex))
                raise HubSyncError
        except Exception as ex:
            self.__hub_sync_event.set()
            self.__hub_sync_lock.release()
            raise ex
        self.__hub_sync_event.set()
        self.__hub_sync_lock.release()

    def __addDevice(self, device: Device, worker: bool = False) -> None:
        if self.__hub_init:
            self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(current_thread())
        try:
            logger.info("adding device '{}' to platform ...".format(device.id))
            access_token = self.__auth.getAccessToken()
            req = http.Request(
                url="https://{}/{}/{}-{}".format(
                    cc_conf.api.host,
                    cc_conf.api.device_endpt,
                    cc_conf.device.id_prefix,
                    http.urlEncode(device.id)
                ),
                method=http.Method.GET,
                headers={"Authorization": "Bearer {}".format(access_token)},
                timeout=cc_conf.api.request_timeout
            )
            resp = req.send()
            if resp.status == 404:
                req = http.Request(
                    url="https://{}/{}".format(cc_conf.api.host, cc_conf.api.device_endpt),
                    method=http.Method.POST,
                    body={
                        "name": device.name,
                        "device_type": device.type,
                        "uri": "{}-{}".format(cc_conf.device.id_prefix, device.id),
                        "tags": device.tags
                        # "img": device.img_url
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.api.request_timeout
                )
                resp = req.send()
                if not resp.status == 200:
                    logger.error(
                        "adding device '{}' to platform failed - {} {}".format(device.id, resp.status, resp.body)
                    )
                    raise DeviceAddError
                logger.debug(
                    "adding device '{}' to platform - waiting {}s for eventual consistency".format(
                        device.id,
                        cc_conf.api.eventual_consistency_delay
                    )
                )
                sleep(cc_conf.api.eventual_consistency_delay)
                logger.info("adding device '{}' to platform successful".format(device.id))
                device_atr = jsonLoads(resp.body)
                __class__.__setMangledAttr(device, "remote_id", device_atr["id"])
            elif resp.status == 200:
                logger.warning("adding device '{}' to platform - device exists - updating device ...".format(device.id))
                device_atr = jsonLoads(resp.body)
                __class__.__setMangledAttr(device, "remote_id", device_atr["id"])
                # if not device.img_url == device_atr["img"]:
                #     device.img_url = device_atr["img"]
                self.__updateDevice(device)
            else:
                logger.error("adding device '{}' to platform failed - {} {}".format(device.id, resp.status, resp.body))
                raise DeviceAddError
        except NoTokenError:
            logger.error("adding device '{}' to platform failed - could not retrieve access token".format(device.id))
            raise DeviceAddError
        except (http.SocketTimeout, http.URLError) as ex:
            logger.error("adding device '{}' to platform failed - {}".format(device.id, ex))
            raise DeviceAddError
        except JSONDecodeError as ex:
            logger.warning("adding device '{}' to platform - could not decode response - {}".format(device.id, ex))
        except KeyError as ex:
            logger.warning("adding device '{}' to platform - malformed response - missing key {}".format(device.id, ex))

    def __deleteDevice(self, device_id: str, worker: bool = False) -> None:
        if self.__hub_init:
            self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(current_thread())
        try:
            logger.info("deleting device '{}' from platform ...".format(device_id))
            access_token = self.__auth.getAccessToken()
            req = http.Request(
                url="https://{}/{}/{}-{}".format(
                    cc_conf.api.host,
                    cc_conf.api.device_endpt,
                    cc_conf.device.id_prefix,
                    http.urlEncode(device_id)
                ),
                method=http.Method.DELETE,
                headers={"Authorization": "Bearer {}".format(access_token)},
                timeout=cc_conf.api.request_timeout
            )
            resp = req.send()
            if resp.status == 200:
                logger.info("deleting device '{}' from platform successful".format(device_id))
            elif resp.status == 404:
                logger.warning("deleting device '{}' from platform - device not found".format(device_id))
            else:
                logger.error(
                    "deleting device '{}' from platform failed - {} {}".format(device_id, resp.status, resp.body)
                )
                raise DeviceDeleteError
        except NoTokenError:
            logger.error(
                "deleting device '{}' from platform failed - could not retrieve access token".format(device_id)
            )
            raise DeviceDeleteError
        except (http.SocketTimeout, http.URLError) as ex:
            logger.error("deleting device '{}' from platform failed - {}".format(device_id, ex))
            raise DeviceDeleteError

    def __updateDevice(self, device: Device) -> None:
        try:
            logger.info("updating device '{}' on platform ...".format(device.id))
            access_token = self.__auth.getAccessToken()
            req = http.Request(
                url="https://{}/{}/{}-{}".format(
                    cc_conf.api.host,
                    cc_conf.api.device_endpt,
                    cc_conf.device.id_prefix,
                    http.urlEncode(device.id)
                ),
                method=http.Method.PUT,
                body={
                    "id": device.remote_id,
                    "name": device.name,
                    "device_type": device.type,
                    "uri": "{}-{}".format(cc_conf.device.id_prefix, device.id),
                    "tags": device.tags
                    # "img": device.img_url
                },
                content_type=http.ContentType.json,
                headers={"Authorization": "Bearer {}".format(access_token)},
                timeout=cc_conf.api.request_timeout
            )
            resp = req.send()
            if resp.status == 200:
                logger.info("updating device '{}' on platform successful".format(device.id))
            elif resp.status == 404:
                logger.error("updating device '{}' on platform failed - device not found".format(device.id))
                raise DeviceNotFoundError
            else:
                logger.error(
                    "updating device '{}' on platform failed - {} {}".format(device.id, resp.status, resp.body)
                )
                raise DeviceUpdateError
        except NoTokenError:
            logger.error("updating device '{}' on platform failed - could not retrieve access token".format(device.id))
            raise DeviceUpdateError
        except (http.SocketTimeout, http.URLError) as ex:
            logger.error("updating device '{}' on platform failed - {}".format(device.id, ex))
            raise DeviceUpdateError

    def __onConnect(self) -> None:
        self.__connected_flag = True
        logger.info(
            "connecting to '{}' on '{}' successful".format(
                cc_conf.connector.host,
                cc_conf.connector.port
            )
        )
        if self.__connect_clbk:
            clbk_thread = Thread(target=self.__connect_clbk, args=(self, ), name="user-connect-callback", daemon=True)
            clbk_thread.start()

    def __onDisconnect(self, code: int, reason: str) -> None:
        self.__connected_flag = False
        if code > 0:
            log_msg = "unexpected disconnect - {}".format(reason)
            if self.__reconnect_flag:
                logger.warning(log_msg)
            else:
                logger.error(log_msg)
        else:
            logger.info("disconnected by user")
        if self.__disconnect_clbk:
            clbk_thread = Thread(
                target=self.__disconnect_clbk,
                args=(self, ),
                name="user-disconnect-callback",
                daemon=True
            )
            clbk_thread.start()
        if self.__reconnect_flag:
            reconnect_thread = Thread(target=self.__reconnect, name="reconnect", daemon=True)
            reconnect_thread.start()

    def __connect(self, event_worker) -> None:
        self.__connect_lock.acquire()
        if self.__connected_flag:
            self.__connect_lock.release()
            logger.error(
                "connecting to '{}' on '{}' failed - already connected".format(
                    cc_conf.connector.host,
                    cc_conf.connector.port
                )
            )
            raise RuntimeError("already connected")
        logger.info("connecting to '{}' on '{}' ... ".format(cc_conf.connector.host, cc_conf.connector.port))
        if self.__comm:
            self.__comm.reset(
                cc_conf.hub.id if self.__hub_init else md5(bytes(cc_conf.credentials.user, "UTF-8")).hexdigest()
            )
        else:
            if not cc_conf.connector.tls:
                logger.warning("TLS encryption disabled")
            self.__comm = mqtt.Client(
                client_id=cc_conf.hub.id if self.__hub_init else md5(
                    bytes(cc_conf.credentials.user, "UTF-8")
                ).hexdigest(),
                msg_retry=cc_conf.connector.msg_retry,
                keepalive=cc_conf.connector.keepalive,
                loop_time=cc_conf.connector.loop_time,
                tls=cc_conf.connector.tls
            )
            self.__comm.on_connect = self.__onConnect
            self.__comm.on_disconnect = self.__onDisconnect
            self.__comm.on_message = self.__handleCommand
        def on_done():
            if event_worker.exception:
                try:
                    raise event_worker.exception
                except mqtt.ConnectError as ex:
                    event_worker.exception = ConnectError(ex)
                    log_msg = "connecting to '{}' on '{}' failed - {}".format(
                        cc_conf.connector.host,
                        cc_conf.connector.port,
                        ex
                    )
                    if self.__reconnect_flag:
                        logger.warning(log_msg)
                    else:
                        logger.error(log_msg)
            self.__connect_lock.release()
        event_worker.usr_method = on_done
        self.__comm.connect(
            host=cc_conf.connector.host,
            port=cc_conf.connector.port,
            usr=cc_conf.credentials.user,
            pw=cc_conf.credentials.pw,
            event_worker=event_worker
        )

    def __reconnect(self, retry: int = 0):
        while not self.__connected_flag:
            if not self.__reconnect_flag:
                break
            retry += 1
            if retry > 0:
                duration = __class__.__calcDuration(
                    min_duration=cc_conf.connector.reconn_delay_min,
                    max_duration=cc_conf.connector.reconn_delay_max,
                    retry_num=retry,
                    factor=cc_conf.connector.reconn_delay_factor
                )
                minutes, seconds = divmod(duration, 60)
                if minutes and seconds:
                    logger.info("reconnect in {}m and {}s ...".format(minutes, seconds))
                elif seconds:
                    logger.info("reconnect in {}s ...".format(seconds))
                elif minutes:
                    logger.info("reconnect in {}m ...".format(minutes))
                sleep(duration)
            worker = EventWorker(
                target=self.__connect,
                name="connect"
            )
            future = worker.start()
            future.wait()

    def __connectDevice(self, device: Device, event_worker) -> None:
        logger.info("connecting device '{}' to platform ...".format(device.id))
        if not self.__connected_flag:
            logger.error("connecting device '{}' to platform failed - not connected".format(device.id))
            raise NotConnectedError
        try:
            def on_done():
                if event_worker.exception:
                    try:
                        raise event_worker.exception
                    except mqtt.SubscribeNotAllowedError as ex:
                        event_worker.exception = DeviceConnectNotAllowedError(ex)
                        logger.error("connecting device '{}' to platform failed - not allowed".format(device.id))
                    except mqtt.SubscribeError as ex:
                        event_worker.exception = DeviceConnectError(ex)
                        logger.error("connecting device '{}' to platform failed - {}".format(device.id, ex))
                    except mqtt.NotConnectedError:
                        event_worker.exception = NotConnectedError
                        logger.error("connecting device '{}' to platform failed - not connected".format(device.id))
                else:
                    logger.info("connecting device '{}' to platform successful".format(device.id))
            event_worker.usr_method = on_done
            self.__comm.subscribe(
                topic="command/{}/+".format(__class__.__prefixDeviceID(device.id)),
                qos=mqtt.qos_map.setdefault(cc_conf.connector.qos, 1),
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error("connecting device '{}' to platform failed - not connected".format(device.id))
            raise NotConnectedError
        except mqtt.SubscribeError as ex:
            logger.error("connecting device '{}' to platform failed - {}".format(device.id, ex))
            raise DeviceConnectError

    def __disconnectDevice(self, device: Device, event_worker) -> None:
        logger.info("disconnecting device '{}' from platform ...".format(device.id))
        if not self.__connected_flag:
            logger.error("disconnecting device '{}' from platform failed - not connected".format(device.id))
            raise NotConnectedError
        try:
            def on_done():
                if event_worker.exception:
                    try:
                        raise event_worker.exception
                    except Exception as ex:
                        event_worker.exception = DeviceDisconnectError(ex)
                        logger.error("disconnecting device '{}' from platform failed - {}".format(device.id, ex))
                else:
                    logger.info("disconnecting device '{}' from platform successful".format(device.id))
            event_worker.usr_method = on_done
            self.__comm.unsubscribe(
                topic="command/{}/+".format(__class__.__prefixDeviceID(device.id)),
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error("disconnecting device '{}' from platform failed - not connected".format(device.id))
            raise NotConnectedError
        except mqtt.UnsubscribeError as ex:
            logger.error("disconnecting device '{}' from platform failed - {}".format(device.id, ex))
            raise DeviceDisconnectError

    def __handleCommand(self, envelope: Union[str, bytes], uri: Union[str, bytes]) -> None:
        logger.debug("received command ...\nservice uri: '{}'\ncommand: '{}'".format(uri, envelope))
        try:
            uri = uri.split("/")
            envelope = jsonLoads(envelope)
            self.__cmd_queue.put_nowait(
                Envelope(
                    device_id=__class__.__parseDeviceID(uri[1]),
                    service_uri=uri[2],
                    message=Message(
                        data=envelope["payload"].setdefault("data", str()),
                        metadata=envelope["payload"].setdefault("metadata", str())
                    ),
                    corr_id=envelope["correlation_id"]
                )
            )
        except JSONDecodeError as ex:
            logger.error("could not parse command - '{}'\nservice uri: '{}'\ncommand: '{}'".format(ex, uri, envelope))
        except (KeyError, AttributeError) as ex:
            logger.error(
                "malformed service uri or command - '{}'\nservice uri: '{}'\ncommand: '{}'".format(ex, uri, envelope)
            )
        except QueueFull:
            logger.error(
                "could not route command to user - queue full - \nservice uri: '{}'\ncommand: '{}'".format(
                    uri,
                    envelope
                )
            )

    def __send(self, handler: str, envelope: Envelope, event_worker):
        logger.info("sending {} '{}' to platform ...".format(handler, envelope.correlation_id))
        if not self.__connected_flag:
            logger.error("sending {} '{}' to platform failed - not connected".format(handler, envelope.correlation_id))
            raise NotConnectedError
        try:
            def on_done():
                if event_worker.exception:
                    try:
                        raise event_worker.exception
                    except Exception as ex:
                        if handler == _SendHandler.event:
                            event_worker.exception = SendEventError(ex)
                        elif handler == _SendHandler.response:
                            event_worker.exception = SendResponseError(ex)
                        else:
                            event_worker.exception = SendError(ex)
                        logger.error(
                            "sending {} '{}' to platform failed - {}".format(handler, envelope.correlation_id, ex)
                        )
                elif mqtt.qos_map.setdefault(cc_conf.connector.qos, 1) > 0:
                    logger.info("sending {} '{}' to platform successful".format(handler, envelope.correlation_id))
            event_worker.usr_method = on_done
            self.__comm.publish(
                topic="{}/{}/{}".format(handler, __class__.__prefixDeviceID(envelope.device_id), envelope.service_uri),
                payload=jsonDumps(dict(envelope.message)) if handler is _SendHandler.event else jsonDumps(dict(envelope)),
                qos=mqtt.qos_map.setdefault(cc_conf.connector.qos, 1),
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error("sending {} '{}' to platform failed - not connected".format(handler, envelope.correlation_id))
            raise NotConnectedError
        except mqtt.PublishError as ex:
            logger.error("sending {} '{}' to platform failed - {}".format(handler, envelope.correlation_id, ex))
            if handler == _SendHandler.event:
                raise SendEventError
            elif handler == _SendHandler.response:
                raise SendResponseError
            else:
                raise SendError

    # ------------- user methods ------------- #

    def setConnectClbk(self, func: Callable[['Client'], None]) -> None:
        """
        Set a callback function to be called when the client successfully connects to the platform.
        :param func: User function.
        :return: None.
        """
        if not callable(func):
            raise TypeError(type(func))
        with self.__set_clbk_lock:
            self.__connect_clbk = func

    def setDisconnectClbk(self, func: Callable[['Client'], None]) -> None:
        """
        Set a callback function to be called when the client disconnects from the platform.
        :param func: User function.
        :return: None.
        """
        if not callable(func):
            raise TypeError(type(func))
        with self.__set_clbk_lock:
            self.__disconnect_clbk = func

    def initHub(self, asynchronous: bool = False) -> Optional[Future]:
        """
        Initialize a hub. Check if hub exists and create new hub if necessary.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        if asynchronous:
            worker = ThreadWorker(target=self.__initHub, name="init-hub", daemon=True)
            future = worker.start()
            return future
        else:
            self.__initHub()

    def syncHub(self, devices: List[Device], asynchronous: bool = False) -> Optional[Future]:
        """
        Synchronize a hub. Associate devices managed by the client with the hub and update hub name.
        Devices must be added via addDevice.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not type(devices) is list:
            raise TypeError(type(devices))
        for device in devices:
            if not __class__.__isDevice(device):
                raise TypeError(type(device))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        if asynchronous:
            worker = ThreadWorker(target=self.__syncHub, args=(devices, ), name="sync-hub", daemon=True)
            future = worker.start()
            return future
        else:
            self.__syncHub(devices)

    def addDevice(self, device: Device, asynchronous: bool = False) -> Optional[Future]:
        """
        Add a device to local device manager and remote platform. Blocks by default.
        :param device: Device object.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not __class__.__isDevice(device):
            raise TypeError(type(device))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        if asynchronous:
            worker = ThreadWorker(
                target=self.__addDevice,
                args=(device, True),
                name="add-device-{}".format(device.id),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__addDevice(device)

    def deleteDevice(self, device: Union[Device, str], asynchronous: bool = False) -> Optional[Future]:
        """
        Delete a device from local device manager and remote platform. Blocks by default.
        :param device: Device ID or Device object.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if __class__.__isDevice(device):
            device = device.id
        if not type(device) is str:
            raise TypeError(type(device))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        if asynchronous:
            worker = ThreadWorker(
                target=self.__deleteDevice,
                args=(device, True),
                name="delete-device-{}".format(device),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__deleteDevice(device)

    def updateDevice(self, device: Device, asynchronous: bool = False) -> Optional[Future]:
        """
        Update a device on the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not __class__.__isDevice(device):
            raise TypeError(type(device))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        if asynchronous:
            worker = ThreadWorker(
                target=self.__updateDevice,
                args=(device, ),
                name="update-device-{}".format(device.id),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__updateDevice(device)

    def connect(self, reconnect: bool = False, asynchronous: bool = False) -> Optional[Future]:
        """
        Connect to platform message broker.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not type(reconnect) is bool:
            raise TypeError(type(reconnect))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        self.__reconnect_flag = reconnect
        if self.__reconnect_flag:
            worker = ThreadWorker(
                target=self.__reconnect,
                args=(-1,),
                name="connect",
                daemon=True
            )
            future = worker.start()
        else:
            worker = EventWorker(
                target=self.__connect,
                name="connect"
            )
            future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()

    def disconnect(self) -> None:
        """
        Disconnect from platform message broker.
        :return: None.
        """
        self.__reconnect_flag = False
        try:
            self.__comm.disconnect()
            logger.info("disconnecting ...")
        except mqtt.NotConnectedError:
            raise NotConnectedError

    def connectDevice(self, device: Device, asynchronous: bool = False) -> Optional[Future]:
        """
        Connect a device to the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not __class__.__isDevice(device):
            raise TypeError(type(device))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        worker = EventWorker(
            target=self.__connectDevice,
            args=(device, ),
            name="connect-device-{}".format(device.id)
        )
        future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()

    def disconnectDevice(self, device: Device, asynchronous: bool = False) -> Optional[Future]:
        """
        Disconnect a device from the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not __class__.__isDevice(device):
            raise TypeError(type(device))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        worker = EventWorker(
            target=self.__disconnectDevice,
            args=(device,),
            name="disconnect-device-{}".format(device.id)
        )
        future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()

    def receiveCommand(self, block: bool = True, timeout: Optional[Union[int, float]] = None) -> Envelope:
        """
        Receive a command.
        :param block: If 'True' blocks until a command is available.
        :param timeout: Return after set amount of time if no command is available.
        :return: Envelope object.
        """
        if not type(block) is bool:
            raise TypeError(type(block))
        if not type(timeout) in (int, float, type(None)):
            raise TypeError(type(timeout))
        try:
            return self.__cmd_queue.get(block=block, timeout=timeout)
        except QueueEmpty:
            raise CommandQueueEmptyError

    def sendResponse(self, envelope: Envelope, asynchronous: bool = False) -> Optional[Future]:
        """
        Send a response to the platform after handling a command.
        :param envelope: Envelope object received from a command via receiveCommand.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not type(envelope) is Envelope:
            raise TypeError(type(envelope))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        worker = EventWorker(
            target=self.__send,
            args=(_SendHandler.response, envelope),
            name="send-response-".format(envelope.correlation_id),
        )
        future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()

    def emmitEvent(self, envelope: Envelope, asynchronous: bool = False) -> Optional[Future]:
        """
        Send an event to the platform.
        :param envelope: Envelope object.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not type(envelope) is Envelope:
            raise TypeError(type(envelope))
        if not type(asynchronous) is bool:
            raise TypeError(type(asynchronous))
        worker = EventWorker(
            target=self.__send,
            args=(_SendHandler.event, envelope),
            name="send-event-".format(envelope.correlation_id)
        )
        future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()


    # ------------- class / static methods ------------- #

    @staticmethod
    def __hashDevices(devices: Union[Tuple[Device], List[Device]]) -> str:
        """
        Hash attributes of the provided devices with SHA1.
        :param devices: List or tuple of devices.
        :return: Hash as string.
        """
        hashes = [device.hash for device in devices]
        hashes.sort()
        return sha1("".join(hashes).encode()).hexdigest()

    @staticmethod
    def __prefixDeviceID(device_id: str) -> str:
        """
        Prefix a ID.
        :param device_id: Device ID.
        :return: Prefixed device ID.
        """
        return "{}-{}".format(cc_conf.device.id_prefix, device_id)

    @staticmethod
    def __parseDeviceID(device_id: str) -> str:
        """
        Remove prefix from device ID.
        :param device_id: Device ID with prefix.
        :return: Device ID.
        """
        return device_id.replace("{}-".format(cc_conf.device.id_prefix), "")

    @staticmethod
    def __getMangledAttr(obj: object, attr: str) -> None:
        """
        Read mangled attribute.
        :param obj: Object with mangled attributes.
        :param attr: Name of mangled attribute.
        :return: value of mangled attribute.
        """
        return getattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr))

    @staticmethod
    def __setMangledAttr(obj: object, attr: str, arg: Any) -> None:
        """
        Write to mangled attribute.
        :param obj: Object with mangled attributes.
        :param attr: Name of mangled attribute.
        :param arg: value to be written.
        """
        setattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr), arg)

    @staticmethod
    def __calcNthTerm(a_1: Union[float, int], r: Union[float, int], n: Union[float, int]) -> Union[float, int]:
        """
        Calculates the nth term of a geometric progression (an = a1 * r^(n-1)).
        :param a_1: First term.
        :param r: Common ratio.
        :param n: Number of desired term.
        :return: Float or integer.
        """
        return a_1 * r ** (n - 1)

    @staticmethod
    def __calcDuration(min_duration: int, max_duration: int, retry_num: int, factor: Union[float, int]) -> int:
        """
        Calculate a value to be used as sleep duration based on a geometric progression.
        Won't return values above max_duration.
        :param min_duration: Minimum value to be returned.
        :param max_duration: Maximum value to be returned.
        :param retry_num: Number iterated by a loop calling the method.
        :param factor: Speed at which the maximum value will be reached.
        :return: Integer.
        """
        base_value = __class__.__calcNthTerm(min_duration, factor, retry_num)
        magnitude = int(log10(ceil(base_value)))+1
        duration = ceil(base_value / 10 ** (magnitude - 1)) * 10 ** (magnitude - 1)
        if duration <= max_duration:
            return duration
        return max_duration

    @staticmethod
    def __isDevice(obj: object) -> bool:
        """
        Check if a object is a Device or a Device subclass
        :param obj: object to check
        :return: Boolean
        """
        if type(obj) is Device or issubclass(type(obj), Device):
            return True
        return False
