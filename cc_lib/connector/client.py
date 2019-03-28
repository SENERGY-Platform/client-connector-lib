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
from .protocol import http
from cc_lib import __version__ as VERSION
from inspect import isclass
from typing import Callable
from threading import Thread
from getpass import getuser
from hashlib import sha1
import datetime, hashlib, base64, json, time


logger = _getLibLogger(__name__.split(".", 1)[-1])


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


class HubProvisionError(ClientError):
    """
    Error during hub provisioning.
    """
    pass


class DeviceProvisionError(ClientError):
    """
    Error during hub provisioning.
    """
    pass


class DeviceExistsError(ClientError):
    """
    Device already added.
    """
    pass


class Client(metaclass=Singleton):
    """
    Client class for client-connector projects.
    To avoid multiple instantiations the Client class implements the singleton pattern.
    Threading is managed internally, wrapping the client in a thread is not necessary.
    """

    def __init__(self, device_manager: Interface):
        """
        Create a Client instance. Set device manager, initiate configuration and library logging facility.
        :param device_manager: object or class implementing the device manager interface.
        """
        self.__device_manager = self.__checkDeviceManager(device_manager)
        initConnectorConf()
        initLogging()
        if not cc_conf.hub.device_id_prefix:
            usr_time_str = '{}{}'.format(
                hashlib.md5(bytes(cc_conf.credentials.user, 'UTF-8')).hexdigest(),
                time.time()
            )
            cc_conf.hub.device_id_prefix = base64.urlsafe_b64encode(
                hashlib.md5(usr_time_str.encode()).digest()
            ).decode().rstrip('=')
        self.__starter_thread = None
        self.__open_id = OpenIdClient(
            "https://{}/{}".format(cc_conf.auth.host, cc_conf.auth.path),
            cc_conf.credentials.user,
            cc_conf.credentials.pw,
            cc_conf.auth.id
        )

    # ------------- internal methods ------------- #

    def __provisionHub(self):
        try:
            devices = self.__device_manager.devices()
            devices_hash = __class__.__hashDevices(devices)
            device_ids = __class__.__listDeviceIDs(devices)
            access_token = self.__open_id.getAccessToken()
            if not cc_conf.hub.id:
                logger.info("initializing new hub ...")
                hub_name = cc_conf.hub.name
                if not hub_name:
                    logger.info("generating hub name ...")
                    hub_name = "{}-{}".format(getuser(), datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
                logger.info("provisioning hub '{}' ...".format(hub_name))
                logger.debug("devices {}".format(device_ids))
                logger.debug("hash '{}'".format(devices_hash))
                req = http.Request(
                    url="https://{}/{}".format(cc_conf.api.host, cc_conf.api.hub),
                    method=http.Method.POST,
                    body={
                        "id": None,
                        "name": hub_name,
                        "hash": devices_hash,
                        "devices": device_ids
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                if devices:
                    logger.info("waiting for eventual consistency")
                    time.sleep(3)
                resp = req.send()
                if not resp.status == 200:
                    logger.error("provisioning failed - {} {}".format(resp.status, resp.body))
                    raise HubProvisionError
                hub = json.loads(resp.body)
                cc_conf.hub.id = hub["id"]
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                if not cc_conf.hub.name:
                    cc_conf.hub.name = hub_name
                logger.info("provisioning completed")
            else:
                logger.info("provisioning hub '{}' ...".format(cc_conf.hub.name))
                logger.debug("devices {}".format(device_ids))
                logger.debug("hash '{}'".format(devices_hash))
                logger.debug("hub ID '{}'".format(cc_conf.hub.id))
                req = http.Request(
                    url="https://{}/{}/{}".format(cc_conf.api.host, cc_conf.api.hub, __class__.__urlEncode(cc_conf.hub.id)),
                    method=http.Method.GET,
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                resp = req.send()
                if resp.status == 200:
                    hub = json.loads(resp.body)
                    if not hub["name"] == cc_conf.hub.name:
                        logger.warning("local name '{}' differs from remote name '{}'".format(cc_conf.hub.name, hub["name"]))
                        logger.info("setting hub name to '{}'".format(hub["name"]))
                        cc_conf.hub.name = hub["name"]
                    if not hub["hash"] == devices_hash:
                        logger.debug("local hash differs from remote hash")
                        logger.info("synchronizing devices ...")
                        req = http.Request(
                            url="https://{}/{}/{}".format(cc_conf.api.host, cc_conf.api.hub, __class__.__urlEncode(cc_conf.hub.id)),
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
                            logger.info("waiting for eventual consistency")
                            time.sleep(3)
                        resp = req.send()
                        if not resp.status == 200:
                            logger.error("provisioning failed - {} could not synchronize devices".format(resp.status, resp.body))
                            raise HubProvisionError
                    logger.info("provisioning completed")
                elif resp.status == 403:
                    logger.error("provisioning failed - {} access forbidden".format(resp.status))
                    raise HubProvisionError
                elif resp.status == 404:
                    logger.error("provisioning failed - {} hub not found".format(resp.status))
                    cc_conf.hub.id = None
                    raise HubProvisionError
                else:
                    logger.error("provisioning failed - {} {}".format(resp.status, resp.body))
                    raise HubProvisionError
        except NoTokenError:
            logger.error("could not retrieve access token")
            raise HubProvisionError
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("provisioning failed - {}".format(ex))
            raise HubProvisionError
        except json.JSONDecodeError as ex:
            logger.error("could not decode response - {}".format(ex))
            raise HubProvisionError
        except KeyError as ex:
            logger.error("malformed response - missing key {}".format(ex))
            raise HubProvisionError


    def __start(self, start_cb=None):
        """
        Start the client.
        :param start_cb: Callback function to be executed after startup.
        :return: None.
        """
        logger.info(12 * "-" + " Starting client-connector v{} ".format(VERSION) + 12 * "-")
        while True:
            try:
                self.__provisionHub()
                # start mqtt client
                break
            except HubProvisionError:
                pass
        if start_cb:
            start_cb()

    # ------------- user methods ------------- #

    def start(self, clbk: Callable[[], None] = None, block: bool = False) -> None:
        """
        Check if starter thread exists, if not create starter thread.
        :param block: If 'True' blocks till start thread finishes
        :param clbk: Callback function to be executed when start thread finishes.
        :return: None.
        """
        if self.__starter_thread:
            raise StartError
        self.__starter_thread = Thread(target=self.__start, args=(clbk,), name="Starter", daemon=True)
        self.__starter_thread.start()
        if block:
            self.__starter_thread.join()


    def emmitEvent(self):
        pass

    def receiveCommand(self):
        pass

    def sendResponse(self):
        pass

    def addDevice(self, device: Device):
        """

        :param device:
        :return: None.
        """
        if not __class__.__checkDevice(device):
            raise TypeError(type(device))
        try:
            access_token = self.__open_id.getAccessToken()
            req = http.Request(
                url="https://{}/{}/{}".format(cc_conf.api.host, cc_conf.api.device, http.urlEncode(device.id)),
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
                        "uri": device.id,
                        "tags": device.tags
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)})
                resp = req.send()
                if not resp.status == 200:
                    raise DeviceProvisionError
            elif resp.status == 200:
                raise DeviceExistsError
            else:
                raise DeviceProvisionError
            self.__device_manager.add(device)
        except NoTokenError:
            logger.error("could not retrieve access token")
            raise DeviceProvisionError
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error("provisioning failed - {}".format(ex))
            raise DeviceProvisionError
        # put on platform

    def deleteDevice(self):
        pass

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
            ids.append(device.id)
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

    @staticmethod
    def __getMangledAttr(obj, attr):
        """
        Read mangled attribute.
        :param obj: Object with mangled attributes.
        :param attr: Name of mangled attribute.
        :return: value of mangled attribute.
        """
        return getattr(obj, "_{}__{}".format(obj.__class__.__name__, attr))

    @staticmethod
    def __setMangledAttr(obj, attr, arg):
        """
        Write to mangled attribute.
        :param obj: Object with mangled attributes.
        :param attr: Name of mangled attribute.
        :param arg: value to be written.
        """
        setattr(obj, "_{}__{}".format(obj.__class__.__name__, attr), arg)
