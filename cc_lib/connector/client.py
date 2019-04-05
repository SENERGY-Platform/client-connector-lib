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
from ..device.manager.interface import Interface
from .singleton import Singleton
from .authentication import OpenIdClient, NoTokenError
from .protocol import http, mqtt
from cc_lib import __version__ as VERSION
from inspect import isclass
from typing import Callable, Union, Any
from getpass import getuser
from hashlib import sha1
import datetime, hashlib, base64, json, time, threading


logger = _getLibLogger(__name__.split(".", 1)[-1])


def _getMangledAttr(obj, attr):
    """
    Read mangled attribute.
    :param obj: Object with mangled attributes.
    :param attr: Name of mangled attribute.
    :return: value of mangled attribute.
    """
    return getattr(obj, "_{}__{}".format(obj.__class__.__name__, attr))


def _setMangledAttr(obj, attr, arg):
    """
    Write to mangled attribute.
    :param obj: Object with mangled attributes.
    :param attr: Name of mangled attribute.
    :param arg: value to be written.
    """
    setattr(obj, "_{}__{}".format(obj.__class__.__name__, attr), arg)


class ClientError(Exception):
    """
    Base error.
    """
    pass


class DeviceMgrSetError(ClientError):
    """
    Device manager can't be set.
    """
    __cases = {
        1: "provided class '{}' does not implement the device manager interface",
        2: "the class '{}' of the provided object does not implement the device manager interface"
    }

    def __init__(self, case, *args):
        super().__init__(__class__.__cases[case].format(*args))


class StartError(ClientError):
    """
    Errors during client startup.
    """
    def __init__(self):
        super().__init__("client-connector already started")


class HubInitializationError(ClientError):
    """
    Error during hub initialization.
    """
    pass


class HubNotInitializedError(ClientError):
    """
    Hub has not been initialized.
    """
    pass


class HubNotFoundError(ClientError):
    """
    Hub ID not on platform.
    """
    pass


class HubSynchronizationError(ClientError):
    """
    Error during hub synchronization.
    """
    pass


class DeviceAddError(ClientError):
    """
    Error while adding a device.
    """
    pass


class DeviceNotFoundError(ClientError):
    """
    Device is missing.
    """
    pass


class DeviceDeleteError(ClientError):
    """
    Error while deleting a device.
    """
    pass


class DeviceUpdateError(ClientError):
    """
    Error while updating a device.
    """
    pass


class FutureNotDoneError(ClientError):
    def __init__(self):
        super().__init__("can't retrieve result - future not done")


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

    def wait(self, timeout: float = None):
        self.__thread.join(timeout)

    def addDoneCallback(self, func: Callable):
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
            except Exception:
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

    def __init__(self, device_manager: Interface):
        """
        Create a Client instance. Set device manager, initiate configuration and library logging facility.
        :param device_manager: object or class implementing the device manager interface.
        """
        self.__device_manager = self.__checkDeviceManager(device_manager)
        initConnectorConf()
        initLogging()
        logger.info(20 * "-" + " client-connector-lib v{} ".format(VERSION) + 20 * "-")
        if not cc_conf.hub.device_id_prefix:
            usr_time_str = '{}{}'.format(
                hashlib.md5(bytes(cc_conf.credentials.user, 'UTF-8')).hexdigest(),
                time.time()
            )
            cc_conf.hub.device_id_prefix = base64.urlsafe_b64encode(
                hashlib.md5(usr_time_str.encode()).digest()
            ).decode().rstrip('=')
        self.__auth = OpenIdClient(
            "https://{}/{}".format(cc_conf.auth.host, cc_conf.auth.path),
            cc_conf.credentials.user,
            cc_conf.credentials.pw,
            cc_conf.auth.id
        )
        self.__comm: mqtt.Client = None
        self.__workers = list()
        self.__hub_sync_event = threading.Event()
        self.__hub_sync_event.set()
        self.__hub_sync_lock = threading.Lock()

    # ------------- internal methods ------------- #

    def __initHub(self):
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
                    url="https://{}/{}".format(cc_conf.api.host, cc_conf.api.hub),
                    method=http.Method.POST,
                    body={
                        "id": None,
                        "name": hub_name,
                        "hash": None,
                        "devices": list()
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                resp = req.send()
                if not resp.status == 200:
                    logger.error("initializing hub failed - {} {}".format(resp.status, resp.body))
                    raise HubInitializationError
                hub = json.loads(resp.body)
                cc_conf.hub.id = hub["id"]
                if not cc_conf.hub.name:
                    cc_conf.hub.name = hub_name
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                logger.info("initializing hub completed")
            else:
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                req = http.Request(
                    url="https://{}/{}/{}".format(cc_conf.api.host, cc_conf.api.hub, http.urlEncode(cc_conf.hub.id)),
                    method=http.Method.HEAD,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                resp = req.send()
                if resp.status == 200:
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

    def __syncHub(self):
        self.__hub_sync_lock.acquire()
        if not cc_conf.hub.id:
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
                devices = self.__device_manager.devices()
                device_ids = __class__.__listDeviceIDs(devices)
                devices_hash = __class__.__hashDevices(devices)
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                logger.debug("devices {}".format(device_ids))
                logger.debug("hash '{}'".format(devices_hash))
                access_token = self.__auth.getAccessToken()
                req = http.Request(
                    url="https://{}/{}/{}".format(cc_conf.api.host, cc_conf.api.hub, http.urlEncode(cc_conf.hub.id)),
                    method=http.Method.GET,
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                resp = req.send()
                if resp.status == 200:
                    hub = json.loads(resp.body)
                    if not hub["name"] == cc_conf.hub.name:
                        logger.warning("synchronizing hub - local name '{}' differs from remote name '{}'".format(cc_conf.hub.name, hub["name"]))
                        logger.info("synchronizing hub - setting hub name to '{}'".format(hub["name"]))
                        cc_conf.hub.name = hub["name"]
                    if not hub["hash"] == devices_hash:
                        logger.debug("synchronizing hub - local hash differs from remote hash")
                        logger.info("synchronizing hub - updating devices ...")
                        req = http.Request(
                            url="https://{}/{}/{}".format(cc_conf.api.host, cc_conf.api.hub, http.urlEncode(cc_conf.hub.id)),
                            method=http.Method.PUT,
                            body={
                                "id": cc_conf.hub.id,
                                "name": cc_conf.hub.name,
                                "hash": devices_hash,
                                "devices": device_ids
                            },
                            content_type=http.ContentType.json,
                            headers={"Authorization": "Bearer {}".format(access_token)})
                        if devices:
                            logger.debug("synchronizing hub - waiting 4s for eventual consistency")
                            time.sleep(4)
                        resp = req.send()
                        if not resp.status == 200:
                            logger.error("synchronizing hub failed - {} could not update devices".format(resp.status, resp.body))
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

    def __addDevice(self, device, worker=False):
        self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(threading.current_thread())
        logger.info("adding device '{}' to device manager ...".format(device.id))
        if self.__device_manager.get(device.id):
            logger.warning("adding device '{}' to device manager - device already in device manager".format(device.id))
        else:
            self.__device_manager.add(device)
        try:
            logger.info("adding device '{}' to platform ...".format(device.id))
            access_token = self.__auth.getAccessToken()
            req = http.Request(
                url="https://{}/{}/{}-{}".format(cc_conf.api.host, cc_conf.api.device, cc_conf.hub.device_id_prefix, http.urlEncode(device.id)),
                method=http.Method.HEAD,
                headers={"Authorization": "Bearer {}".format(access_token)})
            resp = req.send()
            if resp.status == 404:
                req = http.Request(
                    url="https://{}/{}".format(cc_conf.api.host, cc_conf.api.device),
                    method=http.Method.POST,
                    body={
                        "device_type": device.type,
                        "name": device.name,
                        "uri": "{}-{}".format(cc_conf.hub.device_id_prefix, device.id),
                        "tags": device.tags
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                resp = req.send()
                if not resp.status == 200:
                    logger.error("adding device '{}' to platform failed - {} {}".format(device.id, resp.status, resp.body))
                    raise DeviceAddError
                logger.info("adding device '{}' to platform completed".format(device.id))
            elif resp.status == 200:
                logger.warning("adding device '{}' to platform - device already on platform".format(device.id))
            else:
                logger.error("adding device '{}' to platform failed - {} {}".format(device.id, resp.status, resp.body))
                raise DeviceAddError
        except NoTokenError:
            logger.error("adding device '{}' to platform failed - could not retrieve access token".format(device.id))
            raise DeviceAddError
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("adding device '{}' to platform failed - {}".format(device.id, ex))
            raise DeviceAddError

    def __deleteDevice(self, device_id, worker=False):
        self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(threading.current_thread())
        logger.info("deleting device '{}' from device manager ...".format(device_id))
        if self.__device_manager.get(device_id):
            self.__device_manager.delete(device_id)
        else:
            logger.warning("deleting device '{}' - not found in device manager".format(device_id))
        try:
            logger.info("deleting device '{}' from platform ...".format(device_id))
            access_token = self.__auth.getAccessToken()
            req = http.Request(
                url="https://{}/{}/{}-{}".format(cc_conf.api.host, cc_conf.api.device, cc_conf.hub.device_id_prefix, http.urlEncode(device_id)),
                method=http.Method.DELETE,
                headers={"Authorization": "Bearer {}".format(access_token)})
            resp = req.send()
            if resp.status == 200:
                logger.info("deleting device '{}' from platform completed".format(device_id))
            elif resp.status == 404:
                logger.warning("deleting device '{}' from platform - device not found".format(device_id))
            else:
                logger.error("deleting device '{}' from platform failed - {} {}".format(device_id, resp.status, resp.body))
                raise DeviceDeleteError
        except NoTokenError:
            logger.error("deleting device '{}' from platform failed - could not retrieve access token".format(device_id))
            raise DeviceDeleteError
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("deleting device '{}' from platform failed - {}".format(device_id, ex))
            raise DeviceDeleteError

    def __updateDevice(self, device, worker=False):
        # self.__hub_sync_event.wait()
        # if worker:
        #     self.__workers.append(threading.current_thread())
        logger.info("updating device '{}' in device manager ...".format(device.id))
        if self.__device_manager.get(device.id):
            self.__device_manager.update(device)
        else:
            logger.error("updating device '{}' failed - not found in device manager".format(device.id))
            raise DeviceNotFoundError
        try:
            logger.info("updating device '{}' on platform ...".format(device.id))
            access_token = self.__auth.getAccessToken()
            req = http.Request(
                url="https://{}/{}/{}-{}".format(cc_conf.api.host, cc_conf.api.device, cc_conf.hub.device_id_prefix, http.urlEncode(device.id)),
                method=http.Method.HEAD,
                headers={"Authorization": "Bearer {}".format(access_token)})
            resp = req.send()
            if resp.status == 200:
                req = http.Request(
                    url="https://{}/{}/{}-{}".format(cc_conf.api.host, cc_conf.api.device, cc_conf.hub.device_id_prefix, http.urlEncode(device.id)),
                    method=http.Method.PUT,
                    body={
                        "device_type": device.type,
                        "name": device.name,
                        "tags": device.tags
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                resp = req.send()
                if not resp.status == 200:
                    logger.error("updating device '{}' on platform failed - {} {}".format(device.id, resp.status, resp.body))
                    raise DeviceUpdateError
                logger.info("updating device '{}' on platform completed".format(device.id))
            elif resp.status == 404:
                logger.error("updating device '{}' on platform failed - device not found".format(device.id))
                raise DeviceNotFoundError
            else:
                logger.error("updating device '{}' on platform failed - {} {}".format(device.id, resp.status, resp.body))
                raise DeviceUpdateError
        except NoTokenError:
            logger.error("updating device '{}' on platform failed - could not retrieve access token".format(device.id))
            raise DeviceUpdateError
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("updating device '{}' on platform failed - {}".format(device.id, ex))
            raise DeviceUpdateError

    # ------------- user methods ------------- #

    def initHub(self, asynchronous: bool = False) -> Union[Future, None]:
        """

        :param asynchronous:
        :return:
        """
        if asynchronous:
            worker = Worker(target=self.__initHub, name="init-hub", daemon=True)
            future = worker.start()
            return future
        else:
            self.__initHub()

    def syncHub(self, asynchronous: bool = False) -> Union[Future, None]:
        """

        :param asynchronous:
        :return:
        """
        if asynchronous:
            worker = Worker(target=self.__syncHub, name="sync-hub", daemon=True)
            future = worker.start()
            return future
        else:
            self.__syncHub()

    def emmitEvent(self):
        pass

    def receiveCommand(self):
        pass

    def sendResponse(self):
        pass

    def addDevice(self, device: Device, asynchronous: bool = False) -> Union[Future, None]:
        """
        Add a device to local device manager and remote platform. Blocks by default.
        :param device: Device object.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not __class__.__checkDevice(device):
            raise TypeError(type(device))
        if asynchronous:
            worker = Worker(target=self.__addDevice, args=(device, True), name="add-device-{}".format(device.id), daemon=True)
            future = worker.start()
            return future
        else:
            self.__addDevice(device)

    def deleteDevice(self, device_id: str, asynchronous: bool = False) -> Union[Future, None]:
        """
        Delete a device from local device manager and remote platform. Blocks by default.
        :param device_id: Device ID.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not type(device_id) is str:
            raise TypeError(type(device_id))
        if asynchronous:
            worker = Worker(target=self.__deleteDevice, args=(device_id, True), name="delete-device-{}".format(device_id), daemon=True)
            future = worker.start()
            return future
        else:
            self.__deleteDevice(device_id)

    def updateDevice(self, device: Device, asynchronous: bool = False) -> Union[Future, None]:
        """
        Update a device in local device manager and on remote platform.
        :param device: Device object.
        :param asynchronous: If 'True' method returns a ClientFuture object.
        :return: Future or None.
        """
        if not __class__.__checkDevice(device):
            raise TypeError(type(device))
        if asynchronous:
            worker = Worker(target=self.__updateDevice, args=(device, True), name="update-device-{}".format(device.id), daemon=True)
            future = worker.start()
            return future
        else:
            self.__updateDevice(device)

    def connectDevice(self):
        pass

    def disconnectDevice(self):
        pass

    # ------------- class / static methods ------------- #

    @staticmethod
    def __hashDevices(devices) -> str:
        """
        Hash attributes of the provided devices with SHA1.
        :param devices: List, tuple or dict (id:device) of local devices.
        :return: Hash as string.
        """
        if type(devices) is dict:
            devices = list(devices.values())
        hashes = list()
        for device in devices:
            hashes.append(device.hash)
        hashes.sort()
        return sha1("".join(hashes).encode()).hexdigest()

    @staticmethod
    def __listDeviceIDs(devices) -> list:
        """
        List the IDs of the provided devices.
        :param devices: List, tuple or dict (id:device) of local devices.
        :return: List of IDs
        """
        if type(devices) is dict:
            devices = list(devices.values())
        ids = list()
        for device in devices:
            ids.append("{}-{}".format(cc_conf.hub.device_id_prefix, device.id))
        return ids

    @staticmethod
    def __checkDeviceManager(mgr) -> Interface:
        """
        Check if provided object or class implements the device manager interface.
        :param mgr: object or class.
        :return: object or class implementing the device manager interface.
        """
        if isclass(mgr):
            if not issubclass(mgr, Interface):
                raise DeviceMgrSetError(1, mgr.__name__)
        else:
            if not issubclass(type(mgr), Interface):
                raise DeviceMgrSetError(2, type(mgr).__name__)
        return mgr

    @staticmethod
    def __checkDevice(device):
        """
        Check if the type of the provided object is a Device or a Device subclass.
        :param device: object to check.
        :return: None.
        """
        if type(device) is Device or issubclass(type(device), Device):
            return True
        return False
