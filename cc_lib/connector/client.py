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
from cc_lib import __version__ as VERSION
from typing import Callable, Union, Any, Tuple, List, Optional
from getpass import getuser
import datetime
import hashlib
import base64
import json
import time
import threading
import queue


logger = _getLibLogger(__name__.split(".", 1)[-1])


class Future:
    def __init__(self, thread):
        self.__thread = thread

    def result(self) -> Any:
        if not self.__thread.done:
            raise FutureNotDoneError
        if self.__thread.exception:
            raise self.__thread.exception
        return self.__thread.result

    def done(self) -> bool:
        return self.__thread.done

    def running(self) -> bool:
        return not self.__thread.done

    def wait(self, timeout: Optional[float] = None) -> None:
        self.__thread.join(timeout)

    def addDoneCallback(self, func: Callable[[], None]) -> None:
        self.__thread.callback = func


class Worker(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
        super().__init__(group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)
        self.result = None
        self.exception = None
        self.done = False
        self.callback = None

    def run(self):
        try:
            try:
                if self._target:
                    self.result = self._target(*self._args, **self._kwargs)
            finally:
                del self._target, self._args, self._kwargs
        except Exception as ex:
            self.exception = ex
        self.done = True
        if self.callback:
            try:
                self.callback()
            except BaseException:
                logger.exception("exception calling callback for '{}'".format(self.name))

    def start(self) -> Future:
        future = Future(self)
        super().start()
        return future


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
                hashlib.md5(bytes(cc_conf.credentials.user, 'UTF-8')).hexdigest(),
                time.time()
            )
            cc_conf.device.id_prefix = base64.urlsafe_b64encode(
                hashlib.md5(usr_time_str.encode()).digest()
            ).decode().rstrip('=')
        self.__auth = OpenIdClient(
            "https://{}/{}".format(cc_conf.auth.host, cc_conf.auth.path),
            cc_conf.credentials.user,
            cc_conf.credentials.pw,
            cc_conf.auth.id
        )
        self.__device_mgr = DeviceManager()
        self.__comm = None
        self.__cmd_queue = queue.Queue()
        self.__workers = list()
        self.__hub_sync_event = threading.Event()
        self.__hub_sync_event.set()
        self.__hub_sync_lock = threading.Lock()
        self.__hub_init = False
        self.__comm_init = False
        self.__connect_clbk = None
        self.__disconnect_clbk = None
        self.__set_clbk_lock = threading.RLock()

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
                    hub_name = "{}-{}".format(getuser(), datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
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
                hub = json.loads(resp.body)
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
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("initializing hub failed - {}".format(ex))
            raise HubInitializationError
        except json.JSONDecodeError as ex:
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
                    hub = json.loads(resp.body)
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
                            time.sleep(4)
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
            except (http.TimeoutErr, http.URLError) as ex:
                logger.error("synchronizing hub failed - {}".format(ex))
                raise HubSynchronizationError
            except json.JSONDecodeError as ex:
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
        self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(threading.current_thread())
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
                device_atr = json.loads(resp.body)
                __class__.__setMangledAttr(device, "remote_id", device_atr["id"])
                self.__device_mgr.add(device)
            elif resp.status == 200:
                logger.warning("adding device '{}' to platform - device exists - updating device ...".format(device.id))
                self.__device_mgr.add(device)
                device_atr = json.loads(resp.body)
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
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("adding device '{}' to platform failed - {}".format(device.id, ex))
            raise DeviceAddError
        except json.JSONDecodeError as ex:
            logger.warning("adding device '{}' to platform - could not decode response - {}".format(device.id, ex))
        except KeyError as ex:
            logger.warning("adding device '{}' to platform - malformed response - missing key {}".format(device.id, ex))

    def __deleteDevice(self, device_id: str, worker: bool = False) -> None:
        self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(threading.current_thread())
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
        except (http.TimeoutErr, http.URLError) as ex:
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
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("updating device '{}' on platform failed - {}".format(device.id, ex))
            raise DeviceUpdateError

    def __onConnect(self) -> None:
        logger.info(
            "initializing communication completed - connected to '{}' on '{}'".format(
                cc_conf.connector.host,
                cc_conf.connector.port
            )
        )
        connect_thread = threading.Thread(
            target=self.__connectOnlineDevices,
            name="connect-online-devices",
            daemon=True
        )
        connect_thread.start()
        if self.__connect_clbk:
            clbk_thread = threading.Thread(target=self.__connect_clbk, name="user-connect-callback", daemon=True)
            clbk_thread.start()

    def __onDisconnect(self, reason: int) -> None:
        if reason > 0:
            logger.warning("communication stopped unexpectedly")
        else:
            logger.info("stopping communication completed")
        if self.__disconnect_clbk:
            clbk_thread = threading.Thread(target=self.__disconnect_clbk, name="user-disconnect-callback", daemon=True)
            clbk_thread.start()

    def __connectDevice(self, device: Device) -> None:
        __class__.__setMangledAttr(device, "connected_flag", True)
        logger.info("connecting device '{}' to platform ...".format(device.id))
        if not self.__comm:
            logger.error("connecting device '{}' to platform failed - communication not initialized".format(device.id))
            raise CommNotInitializedError
        try:
            self.__comm.subscribe(
                topic="command/{}/+".format(__class__.__prefixDeviceID(device.id)),
                qos=mqtt.qos_map.setdefault(cc_conf.connector.qos, 1),
                timeout=cc_conf.connector.timeout
            )
            logger.info("connecting device '{}' to platform completed".format(device.id))
        except mqtt.NotConnectedError:
            logger.error("connecting device '{}' to platform failed - communication not available".format(device.id))
            raise DeviceConnectError
        except mqtt.SubscribeError as ex:
            logger.error("connecting device '{}' to platform failed - {}".format(device.id, ex))
            raise DeviceConnectError

    def __disconnectDevice(self, device: Device) -> None:
        __class__.__setMangledAttr(device, "connected_flag", False)
        logger.info("disconnecting device '{}' from platform ...".format(device.id))
        if not self.__comm:
            logger.error(
                "disconnecting device '{}' from platform failed - communication not initialized".format(device.id)
            )
            raise CommNotInitializedError
        try:
            self.__comm.unsubscribe(
                topic="command/{}/+".format(__class__.__prefixDeviceID(device.id)),
                timeout=cc_conf.connector.timeout
            )
            logger.info("disconnecting device '{}' from platform completed".format(device.id))
        except mqtt.NotConnectedError:
            logger.error(
                "disconnecting device '{}' from platform failed - communication not available".format(device.id)
            )
            raise DeviceDisconnectError
        except mqtt.UnsubscribeError as ex:
            logger.error("disconnecting device '{}' from platform failed - {}".format(device.id, ex))
            raise DeviceDisconnectError

    def __connectOnlineDevices(self) -> None:
        futures = list()
        for device in self.__device_mgr.devices:
            if __class__.__getMangledAttr(device, "connected_flag"):
                worker = Worker(
                    target=self.__connectDevice,
                    args=(device,),
                    name="connect-device-{}".format(device.id),
                    daemon=True
                )
                futures.append(worker.start())
        for future in futures:
            future.wait()

    def __parseCommand(self, envelope: Union[str, bytes], uri: Union[str, bytes]) -> None:
        try:
            uri = uri.split("/")
            envelope = json.loads(envelope)
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
        except json.JSONDecodeError as ex:
            logger.error(ex)
        except (KeyError, AttributeError) as ex:
            logger.error(ex)
        except queue.Full as ex:
            logger.error(ex)

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
            worker = Worker(target=self.__initHub, name="init-hub", daemon=True)
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
            worker = Worker(target=self.__syncHub, name="sync-hub", daemon=True)
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
            worker = Worker(
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
            worker = Worker(
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
            worker = Worker(
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
        if not self.__hub_init:
            logger.error("hub not initialized - initializing communication not possible")
            raise HubNotInitializedError
        if self.__comm_init:
            logger.error("communication already initialized")
            raise CommInitializedError
        if not self.__comm:
            self.__comm = mqtt.Client(client_id=cc_conf.hub.id, reconnect_delay=cc_conf.connector.reconn_delay)
            self.__comm.on_connect = self.__onConnect
            self.__comm.on_disconnect = self.__onDisconnect
            self.__comm.on_message = self.__parseCommand
        logger.info("initializing communication ...")
        if not cc_conf.connector.tls:
            logger.warning("initializing communication - TLS encryption disabled")
        self.__comm.connect(
            cc_conf.connector.host,
            cc_conf.connector.port,
            cc_conf.credentials.user,
            cc_conf.credentials.pw,
            cc_conf.connector.tls,
            cc_conf.connector.keepalive
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
        logger.info("stopping communication ...")
        self.__comm.disconnect()
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
        if asynchronous:
            worker = Worker(
                target=self.__connectDevice,
                args=(device, ),
                name="connect-device-{}".format(device.id),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__connectDevice(device)

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
        if asynchronous:
            worker = Worker(
                target=self.__disconnectDevice,
                args=(device,),
                name="connect-device-{}".format(device.id),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__disconnectDevice(device)

    def emmitEvent(self, asynchronous: bool = False) -> Optional[Future]:
        pass

    def receiveCommand(self, block: bool = True, timeout: Optional[int] = None) -> Envelope:
        try:
            return self.__cmd_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            raise CommandQueueEmptyError

    def sendResponse(self, asynchronous: bool = False) -> Optional[Future]:
        pass

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
        return hashlib.sha1("".join(hashes).encode()).hexdigest()

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
