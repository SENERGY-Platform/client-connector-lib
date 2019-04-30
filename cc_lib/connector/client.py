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
from ..logger.logger import _getLibLogger, initLogging
from ..device import Device
from .exception import *
from .device_manager import DeviceManager, isDevice
from .singleton import Singleton
from .auth import OpenIdClient, NoTokenError
from .protocol import http, mqtt
from .message import Envelope, Message
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


logger = _getLibLogger(__name__.split(".", 1)[-1])


class SendHandler:
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
        self.__device_mgr = DeviceManager()
        self.__comm: mqtt.Client = None
        self.__comm_init = False
        self.__cmd_queue = Queue()
        self.__workers = list()
        self.__hub_sync_event = Event()
        self.__hub_sync_event.set()
        self.__hub_sync_lock = Lock()
        self.__hub_init = False
        self.__connect_clbk = None
        self.__disconnect_clbk = None
        self.__set_clbk_lock = RLock()
        self.__comm_retry = 0

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
                    timeout=cc_conf.api.req_timeout
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
                logger.info("initializing hub completed")
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
                    timeout=cc_conf.api.req_timeout
                )
                resp = req.send()
                if resp.status == 200:
                    self.__hub_init = True
                    logger.info("initializing hub completed")
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

    def __syncHub(self) -> None:
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
                devices = self.__device_mgr.devices
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
                    timeout=cc_conf.api.req_timeout
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
                            timeout=cc_conf.api.req_timeout
                        )
                        if devices:
                            logger.debug("synchronizing hub - waiting 4s for eventual consistency")
                            sleep(4)
                        resp = req.send()
                        if not resp.status == 200:
                            logger.error(
                                "synchronizing hub failed - {} could not update devices".format(resp.status, resp.body)
                            )
                            raise HubSynchronizationError
                    logger.info("synchronizing hub completed")
                elif resp.status == 404:
                    logger.error("synchronizing hub failed - hub not found on platform")
                    cc_conf.hub.id = None
                    raise HubNotFoundError
                else:
                    logger.error("synchronizing hub failed - {} {}".format(resp.status, resp.body))
                    raise HubSynchronizationError
            except NoTokenError:
                logger.error("synchronizing hub failed - could not retrieve access token")
                raise HubSynchronizationError
            except (http.SocketTimeout, http.URLError) as ex:
                logger.error("synchronizing hub failed - {}".format(ex))
                raise HubSynchronizationError
            except JSONDecodeError as ex:
                logger.error("synchronizing hub failed - could not decode response - {}".format(ex))
                raise HubSynchronizationError
            except KeyError as ex:
                logger.error("synchronizing hub failed - malformed response - missing key {}".format(ex))
                raise HubSynchronizationError
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
                timeout=cc_conf.api.req_timeout
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
                    timeout=cc_conf.api.req_timeout
                )
                resp = req.send()
                if not resp.status == 200:
                    logger.error(
                        "adding device '{}' to platform failed - {} {}".format(device.id, resp.status, resp.body)
                    )
                    raise DeviceAddError
                logger.info("adding device '{}' to platform completed".format(device.id))
                device_atr = jsonLoads(resp.body)
                __class__.__setMangledAttr(device, "remote_id", device_atr["id"])
                self.__device_mgr.add(device)
            elif resp.status == 200:
                logger.warning("adding device '{}' to platform - device exists - updating device ...".format(device.id))
                self.__device_mgr.add(device)
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
        self.__device_mgr.delete(device_id)
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
                timeout=cc_conf.api.req_timeout
            )
            resp = req.send()
            if resp.status == 200:
                logger.info("deleting device '{}' from platform completed".format(device_id))
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
                timeout=cc_conf.api.req_timeout
            )
            resp = req.send()
            if resp.status == 200:
                logger.info("updating device '{}' on platform completed".format(device.id))
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
        self.__comm_retry = 0
        logger.info(
            "communication established - connected to '{}' on '{}'".format(
                cc_conf.connector.host,
                cc_conf.connector.port
            )
        )
        connect_devices_thread = Thread(
            target=self.__connectOnlineDevices,
            name="connect-online-devices",
            daemon=True
        )
        connect_devices_thread.start()
        if self.__connect_clbk:
            clbk_thread = Thread(target=self.__connect_clbk, name="user-connect-callback", daemon=True)
            clbk_thread.start()

    def __onDisconnect(self, reason: Optional[int] = None) -> None:
        if reason is not None:
            if reason > 0:
                logger.warning("communication stopped unexpectedly")
            else:
                logger.info("stopping communication completed")
        else:
            logger.warning("communication could not be established")
        if self.__disconnect_clbk:
            clbk_thread = Thread(target=self.__disconnect_clbk, name="user-disconnect-callback", daemon=True)
            clbk_thread.start()
        self.__comm.reset(cc_conf.hub.id)
        if self.__comm_init:
            comm_restart_thread = Thread(target=self.__restartComm, name="restart-communication", daemon=True)
            comm_restart_thread.start()

    def __restartComm(self):
        self.__comm_retry += 1
        duration = __class__.__calcDuration(
            min_duration=cc_conf.connector.reconn_delay_min,
            max_duration=cc_conf.connector.reconn_delay_max,
            retry_num=self.__comm_retry,
            factor=cc_conf.connector.reconn_delay_factor
        )
        minutes, seconds = divmod(duration, 60)
        if minutes and seconds:
            logger.info("retrying to establish communication in {}m and {}s ...".format(minutes, seconds))
        elif seconds:
            logger.info("retrying to establish communication in {}s ...".format(seconds))
        elif minutes:
            logger.info("retrying to establish communication in {}m ...".format(minutes))
        sleep(duration)
        logger.info("establishing communication ...")
        self.__comm.connect(
            cc_conf.connector.host,
            cc_conf.connector.port,
            cc_conf.credentials.user,
            cc_conf.credentials.pw
        )

    def __connectDevice(self, device: Device, event_worker) -> None:
        __class__.__setMangledAttr(device, "online_flag", True)
        logger.info("connecting device '{}' to platform ...".format(device.id))
        if not self.__comm:
            logger.error("connecting device '{}' to platform failed - communication not initialized".format(device.id))
            raise CommNotInitializedError
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
                else:
                    logger.info("connecting device '{}' to platform completed".format(device.id))
            event_worker.usr_method = on_done
            self.__comm.subscribe(
                topic="command/{}/+".format(__class__.__prefixDeviceID(device.id)),
                qos=mqtt.qos_map.setdefault(cc_conf.connector.qos, 1),
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error("connecting device '{}' to platform failed - communication not available".format(device.id))
            raise CommNotAvailableError
        except mqtt.SubscribeError as ex:
            logger.error("connecting device '{}' to platform failed - {}".format(device.id, ex))
            raise DeviceConnectError

    def __disconnectDevice(self, device: Device, event_worker) -> None:
        __class__.__setMangledAttr(device, "online_flag", False)
        logger.info("disconnecting device '{}' from platform ...".format(device.id))
        if not self.__comm:
            logger.error(
                "disconnecting device '{}' from platform failed - communication not initialized".format(device.id)
            )
            raise CommNotInitializedError
        try:
            def on_done():
                if event_worker.exception:
                    try:
                        raise event_worker.exception
                    except Exception as ex:
                        event_worker.exception = DeviceDisconnectError(ex)
                        logger.error("disconnecting device '{}' from platform failed - {}".format(device.id, ex))
                else:
                    logger.info("disconnecting device '{}' from platform completed".format(device.id))
            event_worker.usr_method = on_done
            self.__comm.unsubscribe(
                topic="command/{}/+".format(__class__.__prefixDeviceID(device.id)),
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error(
                "disconnecting device '{}' from platform failed - communication not available".format(device.id)
            )
            raise CommNotAvailableError
        except mqtt.UnsubscribeError as ex:
            logger.error("disconnecting device '{}' from platform failed - {}".format(device.id, ex))
            raise DeviceDisconnectError

    def __connectOnlineDevices(self) -> None:
        futures = list()
        for device in self.__device_mgr.devices:
            if __class__.__getMangledAttr(device, "online_flag"):
                worker = EventWorker(
                    target=self.__connectDevice,
                    args=(device,),
                    name="connect-device-{}".format(device.id)
                )
                futures.append(worker.start())
        for future in futures:
            future.wait()

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
        if not self.__comm:
            logger.error(
                "sending {} '{}' to platform failed - communication not initialized".format(
                    handler,
                    envelope.correlation_id
                )
            )
            raise CommNotInitializedError
        try:
            def on_done():
                if event_worker.exception:
                    try:
                        raise event_worker.exception
                    except Exception as ex:
                        if handler == SendHandler.event:
                            event_worker.exception = SendEventError(ex)
                        elif handler == SendHandler.response:
                            event_worker.exception = SendResponseError(ex)
                        else:
                            event_worker.exception = SendError(ex)
                        logger.error(
                            "sending {} '{}' to platform failed - {}".format(handler, envelope.correlation_id, ex)
                        )
                elif mqtt.qos_map.setdefault(cc_conf.connector.qos, 1) > 0:
                    logger.info("sending {} '{}' to platform completed".format(handler, envelope.correlation_id))
            event_worker.usr_method = on_done
            self.__comm.publish(
                topic="{}/{}/{}".format(handler, __class__.__prefixDeviceID(envelope.device_id), envelope.service_uri),
                payload=jsonDumps(dict(envelope.message)) if handler is SendHandler.event else jsonDumps(dict(envelope)),
                qos=mqtt.qos_map.setdefault(cc_conf.connector.qos, 1),
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error(
                "sending {} '{}' to platform failed - communication not available".format(
                    handler,
                    envelope.correlation_id
                )
            )
            raise CommNotAvailableError
        except mqtt.PublishError as ex:
            logger.error("sending {} '{}' to platform failed - {}".format(handler, envelope.correlation_id, ex))
            if handler == SendHandler.event:
                raise SendEventError
            elif handler == SendHandler.response:
                raise SendResponseError
            else:
                raise SendError

    # ------------- user methods ------------- #

    def setConnectClbk(self, func: Callable[[], None]) -> None:
        """
        Set a callback function to be called when the client successfully connects to the platform.
        :param func: User function.
        :return: None.
        """
        with self.__set_clbk_lock:
            self.__connect_clbk = func

    def setDisconnectClbk(self, func: Callable[[], None]) -> None:
        """
        Set a callback function to be called when the client disconnects from the platform.
        :param func: User function.
        :return: None.
        """
        with self.__set_clbk_lock:
            self.__disconnect_clbk = func

    def initHub(self, asynchronous: bool = False) -> Optional[Future]:
        """
        Initialize a hub. Check if hub exists and create new hub if necessary.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if asynchronous:
            worker = ThreadWorker(target=self.__initHub, name="init-hub", daemon=True)
            future = worker.start()
            return future
        else:
            self.__initHub()

    def syncHub(self, asynchronous: bool = False) -> Optional[Future]:
        """
        Synchronize a hub. Associate devices managed by the client with the hub and update hub name.
        Devices must be added via addDevice.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if asynchronous:
            worker = ThreadWorker(target=self.__syncHub, name="sync-hub", daemon=True)
            future = worker.start()
            return future
        else:
            self.__syncHub()

    def addDevice(self, device: Device, asynchronous: bool = False) -> Optional[Future]:
        """
        Add a device to local device manager and remote platform. Blocks by default.
        :param device: Device object.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not isDevice(device):
            raise TypeError(type(device))
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
        if isDevice(device):
            device = device.id
        if not type(device) is str:
            raise TypeError(type(device))
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

    def updateDevice(self, device: Union[Device, str], asynchronous: bool = False) -> Optional[Future]:
        """
        Update a device on the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if type(device) is str:
            try:
                device = self.__device_mgr.get(device)
            except KeyError:
                raise DeviceNotFoundError
        if not isDevice(device):
            raise TypeError(type(device))
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

    def getDevice(self, device_id: str) -> Device:
        """
        Get a Device object from the client. Raises an exception if device not found.
        :param device_id: ID of a device.
        :return: Device object.
        """
        try:
            return self.__device_mgr.get(device_id)
        except KeyError:
            raise DeviceNotFoundError

    def listDevices(self) -> Tuple[Device]:
        """
        List all devices managed by the client.
        :return: Tuple of Device objects.
        """
        return self.__device_mgr.devices

    def listDeviceIDs(self) -> Tuple[str]:
        """
        List IDs of all devices managed by the client.
        :return: Tuple of device IDs
        """
        return tuple(device.id for device in self.__device_mgr.devices)

    def initComm(self) -> None:
        """
        Initiate communication with platform. Raise exceptions if hub isn't initialized or if communication
        already initialized.
        :return: None.
        """
        if self.__comm_init:
            logger.error("communication already initialized")
            raise CommInitializedError
        if not self.__comm:
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
        logger.info("initializing communication ...")
        if not cc_conf.connector.tls:
            logger.warning("initializing communication - TLS encryption disabled")
        self.__comm.connect(
            host=cc_conf.connector.host,
            port=cc_conf.connector.port,
            usr=cc_conf.credentials.user,
            pw=cc_conf.credentials.pw
        )
        self.__comm_init = True

    def stopComm(self) -> None:
        """
        Stop communication with platform. Call initComm to reinitialize  communication.
        :return: None.
        """
        if not self.__comm:
            logger.error("communication not initialized")
            raise CommNotInitializedError
        try:
            self.__comm.disconnect()
            logger.info("stopping communication ...")
        except mqtt.NotConnectedError:
            pass
        self.__comm_init = False

    def connectDevice(self, device: Union[Device, str], asynchronous: bool = False) -> Optional[Future]:
        """
        Connect a device to the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        try:
            if isDevice(device):
                self.__device_mgr.get(device.id)
            elif type(device) is str:
                device = self.__device_mgr.get(device)
            else:
                raise TypeError(type(device))
        except KeyError:
            raise DeviceNotFoundError
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

    def disconnectDevice(self, device: Union[Device, str], asynchronous: bool = False) -> Optional[Future]:
        """
        Disconnect a device from the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if type(device) is str:
            try:
                device = self.__device_mgr.get(device)
            except KeyError:
                raise DeviceNotFoundError
        if not isDevice(device):
            raise TypeError(type(device))
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

    def receiveCommand(self, block: bool = True, timeout: Optional[int] = None) -> Envelope:
        """
        Receive a command.
        :param block: If 'True' blocks until a command is available.
        :param timeout: Return after set amount of time if no command is available.
        :return: Envelope object.
        """
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
        worker = EventWorker(
            target=self.__send,
            args=(SendHandler.response, envelope),
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
        worker = EventWorker(
            target=self.__send,
            args=(SendHandler.event, envelope),
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
