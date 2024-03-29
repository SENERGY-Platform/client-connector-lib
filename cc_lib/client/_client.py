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

__all__ = ("Client", "CompletionStrategy")


from .._configuration import cc_conf
from .._util import validate_instance, calc_duration, get_logger
from .._model import DeviceAttribute
from ..types import Device
from ..types.message import CommandEnvelope, CommandResponseEnvelope, EventEnvelope, FogProcessesEnvelope, DeviceMessage, ClientErrorEnvelope, DeviceErrorEnvelope, CommandErrorEnvelope
from ._exception import *
from ._auth import OpenIdClient, NoTokenError
from ._protocol import http, mqtt
from ._asynchron import Future, ThreadWorker, EventWorker
import typing
import datetime
import hashlib
import time
import queue
import threading
import json


logger = get_logger(__name__.rsplit(".", 1)[-1].replace("_", ""))


def _hashDevices(devices: typing.Union[typing.Tuple[Device], typing.List[Device]]) -> str:
    """
    Hash attributes of the provided devices with SHA1.
    :param devices: List or tuple of devices.
    :return: Hash as string.
    """
    hashes = [hashlib.sha1("{}{}".format(device.id, device.name).encode()).hexdigest() for device in devices]
    hashes.sort()
    return hashlib.sha1("".join(hashes).encode()).hexdigest()


class CompletionStrategy:
    optimistic = "optimistic"
    pessimistic = "pessimistic"


class Client:
    """
    Client class for client-connector projects.
    """
    def __init__(self, user: typing.Optional[str] = None, pw: typing.Optional[str] = None, client_id: typing.Optional[str] = None, device_id_prefix: typing.Optional[str] = None, device_attribute_origin: typing.Optional[str] = None, fog_processes: typing.Optional[bool] = False, fog_analytics: typing.Optional[bool] = False):
        """
        Create a Client instance. Set device manager, initiate configuration and library logging facility.
        """
        self.__user = user or cc_conf.credentials.user
        self.__pw = pw or cc_conf.credentials.pw
        self.__device_id_prefix = device_id_prefix
        self.__device_attribute_origin = device_attribute_origin or cc_conf.device_attribute_origin
        self.__fog_processes = fog_processes
        self.__fog_analytics = fog_analytics
        self.__auth = OpenIdClient(cc_conf.api.auth_endpt, self.__user, self.__pw, client_id or cc_conf.credentials.client_id)
        self.__comm = None
        self.__connected_flag = False
        self.__connect_lock = threading.Lock()
        self.__reconnect_flag = False
        self.__cmd_queue = queue.Queue()
        self.__fog_prcs_queue = queue.Queue()
        self.__fog_analyt_queue = queue.Queue()
        self.__workers = list()
        self.__hub_sync_event = threading.Event()
        self.__hub_sync_event.set()
        self.__hub_sync_lock = threading.Lock()
        self.__connect_clbk = None
        self.__disconnect_clbk = None
        self.__set_clbk_lock = threading.RLock()
        self.__hub_id = None
        cmd_sub_topic = cc_conf.api.command_sub_topic.split("/")
        self.__command_sub_topic_map = {
            "identifier": cmd_sub_topic.index(cc_conf.router.command_sub_topic_identifier),
            "device_id": cmd_sub_topic.index("{device_id}"),
            "service_id": cmd_sub_topic.index("+")
        }
        fog_prcs_topic = cc_conf.api.fog_processes_sub_topic.split("/")
        self.__fog_processes_sub_topic_map = {
            "identifier": fog_prcs_topic.index(cc_conf.router.fog_processes_sub_topic_identifier),
            "sub_topic": fog_prcs_topic.index("#")
        }

    # ------------- internal methods ------------- #

    def __init_hub(self, hub_id, hub_name) -> str:
        try:
            logger.info("initializing hub ...")
            access_token = self.__auth.get_access_token()
            if not hub_id:
                logger.info("creating new hub ...")
                if not hub_name:
                    logger.info("generating hub name ...")
                    hub_name = "{}-{}".format(self.__user, "{}Z".format(datetime.datetime.utcnow().isoformat()))
                req = http.Request(
                    url=cc_conf.api.hub_endpt,
                    method=http.Method.POST,
                    body={
                        "id": None,
                        "name": hub_name,
                        "hash": None,
                        "device_local_ids": list()
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.connector.request_timeout
                )
                resp = req.send()
                if not resp.status == 200:
                    logger.error("initializing hub failed - {} {}".format(resp.status, resp.body))
                    raise HubInitializationError
                hub = json.loads(resp.body)
                self.__hub_id = hub["id"]
                logger.debug("hub ID '{}'".format(self.__hub_id))
                logger.info("initializing hub successful")
                return self.__hub_id
            else:
                logger.debug("hub ID '{}'".format(hub_id))
                req = http.Request(
                    url="{}/{}".format(cc_conf.api.hub_endpt, http.url_encode(hub_id)),
                    method=http.Method.HEAD,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.connector.request_timeout
                )
                resp = req.send()
                if resp.status == 200:
                    self.__hub_id = hub_id
                    logger.info("initializing hub successful")
                    return self.__hub_id
                elif resp.status == 404:
                    logger.error("initializing hub failed - hub not found on platform")
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
        except json.JSONDecodeError as ex:
            logger.error("initializing hub failed - could not decode response - {}".format(ex))
            raise HubInitializationError
        except KeyError as ex:
            logger.error("initializing hub failed - malformed response - missing key {}".format(ex))
            raise HubInitializationError

    def __sync_hub(self, devices: typing.List[Device]) -> None:
        self.__hub_sync_lock.acquire()
        if not self.__hub_id:
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
                if self.__device_id_prefix:
                    device_ids = tuple(self.__prefix_device_id(device.id) for device in devices)
                else:
                    device_ids = tuple(device.id for device in devices)
                devices_hash = _hashDevices(devices)
                logger.debug("hub ID '{}'".format(self.__hub_id))
                logger.debug("devices {}".format(device_ids))
                logger.debug("hash '{}'".format(devices_hash))
                access_token = self.__auth.get_access_token()
                req = http.Request(
                    url="{}/{}".format(cc_conf.api.hub_endpt, http.url_encode(self.__hub_id)),
                    method=http.Method.GET,
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.connector.request_timeout
                )
                resp = req.send()
                if resp.status == 200:
                    hub = json.loads(resp.body)
                    if not hub["hash"] == devices_hash:
                        logger.debug("synchronizing hub - local hash differs from remote hash")
                        logger.info("synchronizing hub - updating devices ...")
                        req = http.Request(
                            url="{}/{}".format(cc_conf.api.hub_endpt, http.url_encode(self.__hub_id)),
                            method=http.Method.PUT,
                            body={
                                "id": self.__hub_id,
                                "name": hub["name"],
                                "hash": devices_hash,
                                "device_local_ids": device_ids
                            },
                            content_type=http.ContentType.json,
                            headers={"Authorization": "Bearer {}".format(access_token)},
                            timeout=cc_conf.connector.request_timeout
                        )
                        resp = req.send()
                        if resp.status == 400:
                            logger.error(
                                "synchronizing hub failed - could not update devices"
                            )
                            raise HubSyncDeviceError
                        elif resp.status == 404:
                            logger.error("synchronizing hub failed - hub not found on platform")
                            self.__hub_id = None
                            raise HubNotFoundError
                        elif not resp.status == 200:
                            logger.error(
                                "synchronizing hub failed - {} {}".format(resp.status, resp.body)
                            )
                            raise HubSyncError
                    logger.info("synchronizing hub successful")
                elif resp.status == 404:
                    logger.error("synchronizing hub failed - hub not found on platform")
                    self.__hub_id = None
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
            except json.JSONDecodeError as ex:
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

    def __add_device(self, device: Device, worker: bool = False) -> None:
        if self.__hub_id:
            self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(threading.current_thread())
        try:
            logger.info("adding device '{}' to platform ...".format(device.id))
            access_token = self.__auth.get_access_token()
            req = http.Request(
                url="{}/{}".format(
                    cc_conf.api.device_endpt,
                    http.url_encode(self.__prefix_device_id(device.id)) if self.__device_id_prefix else http.url_encode(device.id)
                ),
                method=http.Method.GET,
                headers={"Authorization": "Bearer {}".format(access_token)},
                timeout=cc_conf.connector.request_timeout
            )
            resp = req.send()
            if resp.status == 404:
                req = http.Request(
                    url=cc_conf.api.device_endpt,
                    method=http.Method.POST,
                    body={
                        "name": device.name,
                        "device_type_id": device.device_type_id,
                        "local_id": self.__prefix_device_id(device.id) if self.__device_id_prefix else device.id,
                        "attributes": self.__add_device_attribute_origin(device.attributes) if device.attributes else device.attributes
                    },
                    content_type=http.ContentType.json,
                    headers={"Authorization": "Bearer {}".format(access_token)},
                    timeout=cc_conf.connector.request_timeout
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
                        cc_conf.connector.eventual_consistency_delay
                    )
                )
                time.sleep(cc_conf.connector.eventual_consistency_delay)
                logger.info("adding device '{}' to platform successful".format(device.id))
                device_atr = json.loads(resp.body)
                setattr(device, '_{}__{}'.format(Device.__name__, "remote_id"), device_atr["id"])
            elif resp.status == 200:
                logger.warning("adding device '{}' to platform - device exists - updating device ...".format(device.id))
                device_atr = json.loads(resp.body)
                setattr(device, '_{}__{}'.format(Device.__name__, "remote_id"), device_atr["id"])
                self.__update_device(device)
            else:
                logger.error("adding device '{}' to platform failed - {} {}".format(device.id, resp.status, resp.body))
                raise DeviceAddError
        except NoTokenError:
            logger.error("adding device '{}' to platform failed - could not retrieve access token".format(device.id))
            raise DeviceAddError
        except (http.SocketTimeout, http.URLError) as ex:
            logger.error("adding device '{}' to platform failed - {}".format(device.id, ex))
            raise DeviceAddError
        except json.JSONDecodeError as ex:
            logger.warning("adding device '{}' to platform - could not decode response - {}".format(device.id, ex))
        except KeyError as ex:
            logger.warning("adding device '{}' to platform - malformed response - missing key {}".format(device.id, ex))

    def __delete_device(self, device_id: str, worker: bool = False) -> None:
        if self.__hub_id:
            self.__hub_sync_event.wait()
        if worker:
            self.__workers.append(threading.current_thread())
        try:
            logger.info("deleting device '{}' from platform ...".format(device_id))
            access_token = self.__auth.get_access_token()
            req = http.Request(
                url="{}/{}".format(
                    cc_conf.api.device_endpt,
                    http.url_encode(self.__prefix_device_id(device_id)) if self.__device_id_prefix else http.url_encode(device_id)
                ),
                method=http.Method.DELETE,
                headers={"Authorization": "Bearer {}".format(access_token)},
                timeout=cc_conf.connector.request_timeout
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

    def __update_device(self, device: Device) -> None:
        try:
            logger.info("updating device '{}' on platform ...".format(device.id))
            access_token = self.__auth.get_access_token()
            req = http.Request(
                url="{}/{}?update-only-same-origin-attributes={}".format(
                    cc_conf.api.device_endpt,
                    http.url_encode(self.__prefix_device_id(device.id)) if self.__device_id_prefix else http.url_encode(device.id),
                    self.__device_attribute_origin
                ),
                method=http.Method.PUT,
                body={
                    "id": device.remote_id,
                    "name": device.name,
                    "device_type_id": device.device_type_id,
                    "local_id": self.__prefix_device_id(device.id) if self.__device_id_prefix else device.id,
                    "attributes": self.__add_device_attribute_origin(device.attributes) if device.attributes else device.attributes
                },
                content_type=http.ContentType.json,
                headers={"Authorization": "Bearer {}".format(access_token)},
                timeout=cc_conf.connector.request_timeout
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

    def __fog_subscribe_on_done(self, event_worker):
        if event_worker.exception:
            try:
                raise event_worker.exception
            except mqtt.SubscribeNotAllowedError:
                logger.error("connecting to fog {} failed - not allowed".format(event_worker.usr_data))
            except mqtt.SubscribeError as ex:
                logger.error("connecting to fog {} failed - {}".format(event_worker.usr_data, ex))
            except mqtt.NotConnectedError:
                logger.error("connecting to fog {} failed - not connected".format(event_worker.usr_data))
            finally:
                try:
                    self.__comm.disconnect()
                    logger.info("disconnecting ...")
                except Exception:
                    pass
        else:
            logger.info("connecting to fog {} successful".format(event_worker.usr_data))

    def __fog_subscribe(self, topic, event_worker):
        logger.info("connecting to fog {} ...".format(event_worker.usr_data))
        if not self.__connected_flag:
            logger.error("connecting to fog {} failed - not connected".format(event_worker.usr_data))
            raise NotConnectedError
        try:
            self.__comm.subscribe(
                topic=topic,
                qos=cc_conf.connector.qos,
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error("connecting to fog {} failed - not connected".format(event_worker.usr_data))
            raise NotConnectedError
        except mqtt.SubscribeError as ex:
            logger.error("connecting to fog {} failed - {}".format(event_worker.usr_data, ex))
            raise FogConnectError

    def __on_connect(self) -> None:
        self.__connected_flag = True
        logger.info(
            "connecting to '{}' on '{}' successful".format(
                cc_conf.connector.host,
                cc_conf.connector.port
            )
        )
        if self.__fog_processes:
            worker = EventWorker(
                target=self.__fog_subscribe,
                args=(cc_conf.api.fog_processes_sub_topic.format(hub_id=self.__hub_id),),
                name="subscribe-fog-processes",
                usr_method=self.__fog_subscribe_on_done,
                usr_data="processes"
            )
            worker.start()
        # if self.__fog_analytics:
        #     worker = EventWorker(
        #         target=self.__fog_subscribe,
        #         args=("fog/control", ),
        #         name="subscribe-fog-analytics",
        #         usr_method=self.__fog_subscribe_on_done,
        #         usr_data="analytics"
        #     )
        #     worker.start()
        if self.__connect_clbk:
            clbk_thread = threading.Thread(target=self.__connect_clbk, args=(self, ), name="user-connect-callback", daemon=True)
            clbk_thread.start()

    def __on_disconnect(self, code: int, reason: str) -> None:
        self.__connected_flag = False
        if code > 0:
            log_msg = "unexpected disconnect - {}".format(reason)
            if self.__reconnect_flag:
                logger.warning(log_msg)
            else:
                logger.error(log_msg)
        else:
            logger.info("client disconnected")
        if self.__disconnect_clbk:
            clbk_thread = threading.Thread(
                target=self.__disconnect_clbk,
                args=(self, ),
                name="user-disconnect-callback",
                daemon=True
            )
            clbk_thread.start()
        if self.__reconnect_flag:
            reconnect_thread = threading.Thread(target=self.__reconnect, name="reconnect", daemon=True)
            reconnect_thread.start()

    def __connect_on_done(self, event_worker):
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
            self.__comm.reset(self.__hub_id or hashlib.md5(bytes(self.__user, "UTF-8")).hexdigest())
        else:
            if not cc_conf.connector.tls:
                logger.warning("TLS encryption disabled")
            self.__comm = mqtt.Client(
                client_id=self.__hub_id or hashlib.md5(bytes(self.__user, "UTF-8")).hexdigest(),
                msg_retry=cc_conf.connector.msg_retry,
                keepalive=cc_conf.connector.keepalive,
                loop_time=cc_conf.connector.loop_time,
                tls=cc_conf.connector.tls,
                clean_session=cc_conf.connector.clean_session,
                logging=cc_conf.connector.low_level_logger
            )
            self.__comm.on_connect = self.__on_connect
            self.__comm.on_disconnect = self.__on_disconnect
            self.__comm.on_message = self.__route_message
        self.__comm.connect(
            host=cc_conf.connector.host,
            port=cc_conf.connector.port,
            usr=self.__user,
            pw=self.__pw,
            event_worker=event_worker
        )

    def __reconnect(self, retry: int = 0):
        while not self.__connected_flag:
            if not self.__reconnect_flag:
                break
            retry += 1
            if retry > 0:
                duration = calc_duration(
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
                time.sleep(duration)
            worker = EventWorker(
                target=self.__connect,
                name="connect",
                usr_method=self.__connect_on_done
            )
            future = worker.start()
            future.wait()

    def __connect_device_on_done(self, event_worker):
        if event_worker.exception:
            try:
                raise event_worker.exception
            except mqtt.SubscribeNotAllowedError as ex:
                event_worker.exception = DeviceConnectNotAllowedError(ex)
                logger.error("connecting device '{}' to platform failed - not allowed".format(event_worker.usr_data))
            except mqtt.SubscribeError as ex:
                event_worker.exception = DeviceConnectError(ex)
                logger.error("connecting device '{}' to platform failed - {}".format(event_worker.usr_data, ex))
            except mqtt.NotConnectedError:
                event_worker.exception = NotConnectedError
                logger.error("connecting device '{}' to platform failed - not connected".format(event_worker.usr_data))
        else:
            logger.info("connecting device '{}' to platform successful".format(event_worker.usr_data))

    def __connect_device(self, device_id: str, event_worker) -> None:
        logger.info("connecting device '{}' to platform ...".format(device_id))
        if not self.__connected_flag:
            logger.error("connecting device '{}' to platform failed - not connected".format(device_id))
            raise NotConnectedError
        try:
            self.__comm.subscribe(
                topic=cc_conf.api.command_sub_topic.format(
                    device_id=self.__prefix_device_id(device_id) if self.__device_id_prefix else device_id
                ),
                qos=cc_conf.connector.qos,
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error("connecting device '{}' to platform failed - not connected".format(device_id))
            raise NotConnectedError
        except mqtt.SubscribeError as ex:
            logger.error("connecting device '{}' to platform failed - {}".format(device_id, ex))
            raise DeviceConnectError

    def __disconnect_device_on_done(self, event_worker):
        if event_worker.exception:
            try:
                raise event_worker.exception
            except Exception as ex:
                event_worker.exception = DeviceDisconnectError(ex)
                logger.error("disconnecting device '{}' from platform failed - {}".format(event_worker.usr_data, ex))
        else:
            logger.info("disconnecting device '{}' from platform successful".format(event_worker.usr_data))

    def __disconnect_device(self, device_id: str, event_worker) -> None:
        logger.info("disconnecting device '{}' from platform ...".format(device_id))
        if not self.__connected_flag:
            logger.error("disconnecting device '{}' from platform failed - not connected".format(device_id))
            raise NotConnectedError
        try:
            self.__comm.unsubscribe(
                topic=cc_conf.api.command_sub_topic.format(
                    device_id=self.__prefix_device_id(device_id) if self.__device_id_prefix else device_id
                ),
                event_worker=event_worker
            )
        except mqtt.NotConnectedError:
            logger.error("disconnecting device '{}' from platform failed - not connected".format(device_id))
            raise NotConnectedError
        except mqtt.UnsubscribeError as ex:
            logger.error("disconnecting device '{}' from platform failed - {}".format(device_id, ex))
            raise DeviceDisconnectError

    def __route_message(self, payload: typing.Union[str, bytes], topic: str):
        try:
            topic_parts = topic.split("/")
            if topic_parts[self.__command_sub_topic_map["identifier"]] == cc_conf.router.command_sub_topic_identifier:
                self.__handle_command(
                    payload=payload,
                    device_id=topic_parts[self.__command_sub_topic_map["device_id"]],
                    service_uri=topic_parts[self.__command_sub_topic_map["service_id"]]
                )
            elif topic_parts[self.__fog_processes_sub_topic_map["identifier"]] == cc_conf.router.fog_processes_sub_topic_identifier:
                self.__handle_fog_process(
                    payload=payload,
                    sub_topic="/".join(topic_parts[self.__fog_processes_sub_topic_map["sub_topic"]:]))
        except Exception as ex:
            logger.error("routing received message failed - {}\ntopic: {}\npayload: {}".format(ex, topic, payload))

    def __handle_fog_process(self, payload: typing.Union[str, bytes], sub_topic: str):
        logger.debug("received fog processes message ...\nsub id: {}\npayload: '{}'".format(sub_topic, payload))
        try:
            self.__fog_prcs_queue.put_nowait(FogProcessesEnvelope(sub_topic=sub_topic, message=payload))
        except Exception as ex:
            logger.error(
                "could not handle fog processes message - {}\nsub topic: {}\npayload: '{}'".format(ex, sub_topic, payload)
            )

    # def __handle_fog_analytics(self, payload: typing.Union[str, bytes]):
    #     logger.debug("received fog analytics message ...\npayload: '{}'".format(payload))

    def __handle_command(self, payload: typing.Union[str, bytes], device_id, service_uri: str) -> None:
        logger.debug(
            "received command message ...\ndevice id: '{}'\nservice uri: '{}'\npayload: '{}'".format(
                device_id,
                service_uri,
                payload
            )
        )
        try:
            payload = json.loads(payload)
            self.__cmd_queue.put_nowait(
                CommandEnvelope(
                    device=self.__parse_device_id(device_id) if self.__device_id_prefix else device_id,
                    service=service_uri,
                    message=DeviceMessage(
                        data=payload["payload"].get("data"),
                        metadata=payload["payload"].get("metadata")
                    ),
                    corr_id=payload["correlation_id"],
                    completion_strategy=payload["completion_strategy"],
                    timestamp=payload["timestamp"]
                )
            )
        except Exception as ex:
            logger.error(
                "could not handle command message - '{}'\ndevice id: '{}'\nservice uri: '{}'\npayload: '{}'".format(
                    ex,
                    device_id,
                    service_uri,
                    payload
                )
            )

    def __send_on_done(self, event_worker):
        if event_worker.exception:
            try:
                raise event_worker.exception
            except Exception as ex:
                event_worker.exception = SendError(ex)
                logger.error(
                    "sending {} '{}' to platform failed - {}".format(
                        event_worker.usr_data.__class__.__name__,
                        event_worker.usr_data.correlation_id, ex
                    )
                )
        elif cc_conf.connector.qos > 0:
            logger.debug(
                "sending {} '{}' to platform successful".format(
                    event_worker.usr_data.__class__.__name__,
                    event_worker.usr_data.correlation_id
                )
            )

    def __send(self, topic: str, payload: str, envelope_type: str, correlation_id: str, event_worker):
        logger.debug("sending {} '{}' to platform ...".format(envelope_type, correlation_id))
        if not self.__connected_flag:
            logger.error(
                "sending {} '{}' to platform failed - not connected".format(envelope_type, correlation_id)
            )
            raise NotConnectedError
        try:
            self.__comm.publish(topic=topic, payload=payload, qos=cc_conf.connector.qos, event_worker=event_worker)
        except mqtt.NotConnectedError:
            logger.error(
                "sending {} '{}' to platform failed - not connected".format(envelope_type, correlation_id)
            )
            raise NotConnectedError
        except mqtt.PublishError as ex:
            logger.error(
                "sending {} '{}' to platform failed - {}".format(envelope_type, correlation_id, ex)
            )
            raise SendError

    def __send_wrapper(self, topic, payload, envelope, asynchronous) -> typing.Optional[Future]:
        validate_instance(asynchronous, bool)
        worker = EventWorker(
            target=self.__send,
            args=(
                topic,
                payload,
                envelope.__class__.__name__,
                envelope.correlation_id
            ),
            name="send-{}-{}".format(envelope.__class__.__name__, envelope.correlation_id),
            usr_method=self.__send_on_done,
            usr_data=envelope
        )
        future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()

    def __prefix_device_id(self, device_id: str) -> str:
        """
        Prefix a ID.
        :param device_id: Device ID.
        :return: Prefixed device ID.
        """
        return "{}-{}".format(self.__device_id_prefix, device_id)

    def __parse_device_id(self, device_id: str) -> str:
        """
        Remove prefix from device ID.
        :param device_id: Device ID with prefix.
        :return: Device ID.
        """
        return device_id.replace("{}-".format(self.__device_id_prefix), "")

    def __add_device_attribute_origin(self, attributes: typing.List[typing.Dict[str, typing.Union[str, int, float]]]):
        for attr in attributes:
            attr[DeviceAttribute.origin] = self.__device_attribute_origin
        return attributes

    # ------------- user methods ------------- #

    def set_connect_clbk(self, func: typing.Callable[['Client'], None]) -> None:
        """
        Set a callback function to be called when the client successfully connects to the platform.
        :param func: User function.
        :return: None.
        """
        if not callable(func):
            raise TypeError(type(func))
        with self.__set_clbk_lock:
            self.__connect_clbk = func

    def set_disconnect_clbk(self, func: typing.Callable[['Client'], None]) -> None:
        """
        Set a callback function to be called when the client disconnects from the platform.
        :param func: User function.
        :return: None.
        """
        if not callable(func):
            raise TypeError(type(func))
        with self.__set_clbk_lock:
            self.__disconnect_clbk = func

    def init_hub(self, hub_id: typing.Optional[str] = None, hub_name: typing.Optional[str] = None, asynchronous: bool = False) -> typing.Union[str, Future]:
        """
        Initialize a hub. Check if hub exists and create new hub if necessary.
        :param hub_id: If none is given a new hub will be created.
        :param hub_name: If none is given a new name will be generated. Only used during hub creation.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future object or Hub ID (str).
        """
        validate_instance(hub_id, (str, type(None)))
        validate_instance(asynchronous, bool)
        if asynchronous:
            worker = ThreadWorker(target=self.__init_hub, args=(hub_id,), name="init-hub", daemon=True)
            future = worker.start()
            return future
        else:
            return self.__init_hub(hub_id=hub_id, hub_name=hub_name)

    def sync_hub(self, devices: typing.List[Device], asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Synchronize a hub. Associate devices managed by the client with the hub and update hub name.
        Devices must be added via addDevice.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(devices, list)
        validate_instance(asynchronous, bool)
        for device in devices:
            validate_instance(device, Device)
        if asynchronous:
            worker = ThreadWorker(target=self.__sync_hub, args=(devices,), name="sync-hub", daemon=True)
            future = worker.start()
            return future
        else:
            self.__sync_hub(devices)

    def add_device(self, device: Device, asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Add a device to local device manager and remote platform. Blocks by default.
        :param device: Device object.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(device, Device)
        validate_instance(asynchronous, bool)
        if asynchronous:
            worker = ThreadWorker(
                target=self.__add_device,
                args=(device, True),
                name="add-device-{}".format(device.id),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__add_device(device)

    def delete_device(self, device: typing.Union[Device, str], asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Delete a device from local device manager and remote platform. Blocks by default.
        :param device: Device ID or Device object.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(device, (Device, str))
        validate_instance(asynchronous, bool)
        if isinstance(device, Device):
            device = device.id
            validate_instance(device, str)
        if asynchronous:
            worker = ThreadWorker(
                target=self.__delete_device,
                args=(device, True),
                name="delete-device-{}".format(device),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__delete_device(device)

    def update_device(self, device: Device, asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Update a device on the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(device, Device)
        validate_instance(asynchronous, bool)
        if asynchronous:
            worker = ThreadWorker(
                target=self.__update_device,
                args=(device, ),
                name="update-device-{}".format(device.id),
                daemon=True
            )
            future = worker.start()
            return future
        else:
            self.__update_device(device)

    def connect(self, reconnect: bool = False, asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Connect to platform message broker.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        if self.__fog_processes and not self.__hub_id:
            raise ConnectError("fog processes requires initialized hub")
        validate_instance(reconnect, bool)
        validate_instance(asynchronous, bool)
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
                name="connect",
                usr_method=self.__connect_on_done
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

    def connect_device(self, device: typing.Union[Device, str], asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Connect a device to the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(device, (Device, str))
        validate_instance(asynchronous, bool)
        if isinstance(device, Device):
            device = device.id
            validate_instance(device, str)
        worker = EventWorker(
            target=self.__connect_device,
            args=(device, ),
            name="connect-device-{}".format(device),
            usr_method=self.__connect_device_on_done,
            usr_data=device
        )
        future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()

    def disconnect_device(self, device: typing.Union[Device, str], asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Disconnect a device from the platform.
        :param device: Device object or device ID.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(device, (Device, str))
        validate_instance(asynchronous, bool)
        if isinstance(device, Device):
            device = device.id
            validate_instance(device, str)
        worker = EventWorker(
            target=self.__disconnect_device,
            args=(device,),
            name="disconnect-device-{}".format(device),
            usr_method=self.__disconnect_device_on_done,
            usr_data=device
        )
        future = worker.start()
        if asynchronous:
            return future
        else:
            future.wait()
            future.result()

    def receive_command(self, block: bool = True, timeout: typing.Optional[typing.Union[int, float]] = None) -> CommandEnvelope:
        """
        Receive a command.
        :param block: If 'True' blocks until a command is available.
        :param timeout: Return after set amount of time if no command is available.
        :return: Envelope object.
        """
        validate_instance(block, bool)
        validate_instance(timeout, (int, float, type(None)))
        try:
            return self.__cmd_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            raise QueueEmptyError

    def send_command_response(self, envelope: CommandResponseEnvelope, asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Send a response to the platform after handling a command.
        :param envelope: Envelope object received from a command via receiveCommand.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(envelope, CommandResponseEnvelope)
        return self.__send_wrapper(
            topic=cc_conf.api.command_response_pub_topic.format(
                device_id=self.__prefix_device_id(envelope.device_id) if self.__device_id_prefix else envelope.device_id,
                service_id=envelope.service_uri
            ),
            payload=json.dumps(dict(envelope)),
            envelope=envelope,
            asynchronous=asynchronous
        )

    def send_event(self, envelope: EventEnvelope, asynchronous: bool = False) -> typing.Optional[Future]:
        """
        Send an event to the platform.
        :param envelope: Envelope object.
        :param asynchronous: If 'True' method returns a Future object.
        :return: Future or None.
        """
        validate_instance(envelope, EventEnvelope)
        return self.__send_wrapper(
            topic=cc_conf.api.event_pub_topic.format(
                device_id=self.__prefix_device_id(envelope.device_id) if self.__device_id_prefix else envelope.device_id,
                service_id=envelope.service_uri
            ),
            payload=json.dumps(dict(envelope.message)),
            envelope=envelope,
            asynchronous=asynchronous
        )

    def receive_fog_processes(self, block: bool = True, timeout: typing.Optional[typing.Union[int, float]] = None) -> FogProcessesEnvelope:
        """
        Receive fog processes and control data.
        :param block: If 'True' blocks until a command is available.
        :param timeout: Return after set amount of time if no data is available.
        :return: FogProcessesEnvelope object.
        """
        validate_instance(block, bool)
        validate_instance(timeout, (int, float, type(None)))
        try:
            return self.__fog_prcs_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            raise QueueEmptyError

    def send_fog_process_sync(self, envelope: FogProcessesEnvelope, asynchronous: bool = False) -> typing.Optional[Future]:
        """
            Send fog processes sync data to the platform.
            :param envelope: FogProcessesEnvelope object.
            :param asynchronous: If 'True' method returns a Future object.
            :return: Future or None.
        """
        validate_instance(envelope, FogProcessesEnvelope)
        return self.__send_wrapper(
            topic=cc_conf.api.fog_processes_pub_topic.format(hub_id=self.__hub_id, sub_topic=envelope.sub_topic),
            payload=envelope.message,
            envelope=envelope,
            asynchronous=asynchronous
        )

    def send_client_error(self, envelope: ClientErrorEnvelope, asynchronous: bool = False) -> typing.Optional[Future]:
        """
            Send a client error to the platform.
            :param envelope: ClientErrorEnvelope object.
            :param asynchronous: If 'True' method returns a Future object.
            :return: Future or None.
        """
        validate_instance(envelope, ClientErrorEnvelope)
        return self.__send_wrapper(
            topic=cc_conf.api.client_error_pub_topic,
            payload=envelope.message,
            envelope=envelope,
            asynchronous=asynchronous
        )

    def send_device_error(self, envelope: DeviceErrorEnvelope, asynchronous: bool = False) -> typing.Optional[Future]:
        """
            Send a device error to the platform.
            :param envelope: ClientErrorEnvelope object.
            :param asynchronous: If 'True' method returns a Future object.
            :return: Future or None.
        """
        validate_instance(envelope, DeviceErrorEnvelope)
        return self.__send_wrapper(
            topic=cc_conf.api.device_error_pub_topic.format(device_id=envelope.device_id),
            payload=envelope.message,
            envelope=envelope,
            asynchronous=asynchronous
        )

    def send_command_error(self, envelope: CommandErrorEnvelope, asynchronous: bool = False) -> typing.Optional[Future]:
        """
            Send a command error to the platform.
            :param envelope: ClientErrorEnvelope object.
            :param asynchronous: If 'True' method returns a Future object.
            :return: Future or None.
        """
        validate_instance(envelope, CommandErrorEnvelope)
        return self.__send_wrapper(
            topic=cc_conf.api.command_error_pub_topic.format(correlation_id=envelope.correlation_id),
            payload=envelope.message,
            envelope=envelope,
            asynchronous=asynchronous
        )
