"""
   Copyright 2018 InfAI (CC SES)

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

try:
    from connector_lib.modules.logger import root_logger
    from connector_lib.modules.singleton import Singleton
    from connector_lib._connector.configuration import VERSION, CONNECTOR_USER, CONNECTOR_PASSWORD, CONNECTOR_WS_ENCRYPTION, CONNECTOR_WS_HOST, CONNECTOR_WS_PORT, GATEWAY_ID, writeConf
    from connector_lib._connector.session import SessionManager
    from connector_lib._connector.websocket import Websocket
    from connector_lib._connector.message import Message, marshalMsg, unmarshalMsg, getMangledAttr, setMangledAttr
    from connector_lib.device import DeviceManagerInterface, Device, _isDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time, hashlib, math
from queue import Queue
from threading import Thread, Event
from inspect import isclass

logger = root_logger.getChild(__name__)


# platform handlers map
handlers = {
    'put_handler': 'put',
    'disconnect_handler': 'disconnect',
    'delete_handler': 'delete',
    'event_handler': 'event',
    'response_handler': 'response',
    'command_handler': 'command',
    'clear_handler': 'clear',
    'commit_handler': 'commit'
}


def _callback(event, message=None):
    """
    Adds a message to an Event and sets it.
    :param event: Event object.
    :param message: Event message.
    """
    event.message = message
    event.set()


def _callAndWaitFor(function, *args, timeout=None, **kwargs):
    """
    Call a method containing an Event and wait for completion.
    :param function: Method with ability to call a callback to set a event.
    :param args: User arguments.
    :param timeout: Time in sec to wait for method to complete.
    :param kwargs: User arguments.
    :return: Event message.
    """
    event = Event()
    event.message = None
    function(functools.partial(_callback, event), *args, **kwargs)
    event.wait(timeout=timeout)
    return event.message


def _interfaceCheck(cls, interface):
    """
    Checks if a class subclasses another class.
    Raises TypeError on mismatch.
    :param cls: Class to check.
    :param interface: Class that should be subclassed.
    :return: Boolean.
    """
    if issubclass(cls, interface):
        return True
    raise TypeError("provided class '{}' must be a subclass of '{}'".format(cls, interface))


def _synchroniseGid(remote_gid):
    """
    Checks if local and remote gateway ID differ and sets new ID.
    :param remote_gid: Remote gateway ID as string.
    """
    global GATEWAY_ID
    if not GATEWAY_ID == remote_gid:
        logger.debug('local and remote gateway ID differ: {} - {}'.format(GATEWAY_ID, remote_gid))
        GATEWAY_ID = remote_gid
        writeConf(section='CONNECTOR', option='gid', value=remote_gid)
        logger.info("set gateway ID: '{}'".format(remote_gid))
        time.sleep(2)
    else:
        logger.debug('local and remote gateway ID match')


def _hashDevices(devices) -> str:
    """
    Hashes provided devices with SHA1.
    :param devices: List, tuple or dict (id:device) of local devices.
    :return: Hash as string.
    """
    if type(devices) not in (dict, list, tuple):
        raise TypeError("please provide devices via dictionary, list or tuple - got '{}'".format(type(devices)))
    if type(devices) is dict:
        devices = list(devices.values())
    hashes = list()
    for device in devices:
        hashes.append(device.hash)
    hashes.sort()
    return hashlib.sha1(''.join(hashes).encode()).hexdigest()


class Client(metaclass=Singleton):
    """
    client-connector for integrating personal IoT projects / devices with the platform.
    To avoid multiple instantiations the Client class implements the singleton pattern.
    The client API uses static methods, thus allowing calls directly from the class or an object.
    Threading is managed internally, wrapping the client in a thread is not necessary.
    """
    __out_queue = Queue()
    __in_queue = Queue()
    __client_queue = Queue()
    __device_manager = None
    __ready = False
    __reconnect_min_delay = 30


    def __init__(self, device_manager, con_callbck=None, discon_callbck=None):
        """
        Creates a Client instance, checks for a device manager, starts session manager, callback handler and router.
        Connects to the platform on first run and returns control to caller.
        :param device_manager: Required (class or object), must implement DeviceManagerInterface.
        :param con_callbck: Method to be called after successful connection to platform.
        :param discon_callbck: Method to be called upon disconnect event.
        """
        if not device_manager:
            raise RuntimeError("a device manager must be provided")
        elif isclass(device_manager):
            if not _interfaceCheck(device_manager, DeviceManagerInterface):
                raise TypeError("'{}' must subclass DeviceManagerInterface".format(device_manager.__name__))
        elif not _interfaceCheck(type(device_manager), DeviceManagerInterface):
            raise TypeError("'{}' must subclass DeviceManagerInterface".format(type(device_manager).__name__))
        logger.info(12 * '*' + ' Starting client-connector v{} '.format(VERSION) + 12 * '*')
        self.__reconnect_attempts = 0
        self.__reconnect_delay = __class__.__reconnect_min_delay
        self.__con_callbck = con_callbck
        self.__discon_callbck = discon_callbck
        __class__.__device_manager = device_manager
        self.__session_manager = SessionManager()
        self.__callback_thread = Thread(target=self.__callbackHandler, name="Callback")
        self.__callback_thread.start()
        self.__router_thread = Thread(target=self.__router, name="Router")
        self.__router_thread.start()
        self.__connect()


    def __callbackHandler(self):
        """
        Execute callbacks from the session manager.
        """
        while True:
            callback, msg_obj = SessionManager.callback_queue.get()
            callback(msg_obj)


    def __router(self):
        """
        Routes tasks / commands to the user and raises events for remaining messages.
        """
        while True:
            msg_str = __class__.__in_queue.get()
            msg_obj = unmarshalMsg(msg_str)
            if msg_obj:
                if getMangledAttr(msg_obj, 'handler') == handlers['command_handler']:
                    __class__.__client_queue.put(msg_obj)
                else:
                    SessionManager.raiseEvent(msg_obj, getMangledAttr(msg_obj, 'token'))


    def __connect(self, wait=None) -> bool:
        """
        Connects to the platform.
        Performs handshake, starts device synchronisation and sets the client-connector to ready on successful connection.
        :param wait: Time in sec to wait until a connection is attempted.
        :return: Boolean.
        """
        if wait:
            if self.__discon_callbck:
                self.__discon_callbck()
            time.sleep(wait)
        credentials = json.dumps({
            'user': CONNECTOR_USER,
            'pw': CONNECTOR_PASSWORD,
            'gid': GATEWAY_ID,
            'token': 'credentials'
        })
        websocket = Websocket(CONNECTOR_WS_ENCRYPTION, CONNECTOR_WS_HOST, CONNECTOR_WS_PORT, self.__reconnect)
        logger.info('trying to connect to platform-connector')
        if _callAndWaitFor(websocket.connect):
            logger.info("connected to platform-connector")
            self.__reconnect_attempts = 0
            self.__reconnect_delay = __class__.__reconnect_min_delay
            logger.debug("starting handshake")
            logger.debug('sending credentials: {}'.format(credentials))
            if _callAndWaitFor(websocket.send, credentials):
                initial_response = _callAndWaitFor(websocket.receive)
                if initial_response:
                    logger.debug('received initial response: {}'.format(initial_response))
                    initial_response = unmarshalMsg(initial_response)
                    if initial_response and initial_response.status == 200 and getMangledAttr(initial_response, 'token') == 'credentials':
                        logger.debug('check if gateway ID needs to be synchronised')
                        _synchroniseGid(initial_response.payload.get('gid'))
                        logger.info('handshake completed')
                        #clear out queue?
                        _callAndWaitFor(websocket.ioStart, __class__.__in_queue, __class__.__out_queue)
                        logger.info('checking if devices need to be synchronised')
                        if self.__synchroniseDevices(initial_response.payload.get('hash')):
                            logger.info('client-connector ready')
                            __class__.__ready = True
                            if self.__con_callbck:
                                self.__con_callbck()
                            return True
                    else:
                        logger.error('handshake failed - {} {}'.format(initial_response.payload, initial_response.status))
                else:
                    logger.error('handshake failed - timed out or connection closed')
            else:
                logger.error('could not initiate handshake')
        else:
            logger.error('could not connect')
        _callAndWaitFor(websocket.shutdown)
        return False


    def __calcGeometricDelay(self):
        """
        Calculates a delay based on a geometric progression.
        """
        exponent = self.__reconnect_attempts / 6
        self.__reconnect_delay = self.__reconnect_delay * 2 ** exponent


    def __getDelay(self):
        """
        Round up the geometric delay to a more reasonable value and return it. Won't return values above 300.
        :return: Integer.
        """
        if self.__reconnect_delay < 100:
            return math.ceil(self.__reconnect_delay / 10) * 10
        else:
            delay = math.ceil(self.__reconnect_delay / 100) * 100
            if delay <= 300:
                return delay
            return 300


    def __reconnect(self):
        """
        Calls __connect(wait=self.__getDelay()) wrapped in a thread on a reconnect event.
        Advances the reconnect attempt and calls __calcGeometricDelay() if necessary.
        """
        __class__.__ready = False
        reconnect = Thread(target=self.__connect, name='Reconnect', args=(self.__getDelay(), ))
        logger.info("reconnecting in {}s".format(self.__getDelay()))
        if self.__reconnect_delay <= 200:
            self.__calcGeometricDelay()
            self.__reconnect_attempts = self.__reconnect_attempts + 1
        reconnect.start()


    def __synchroniseDevices(self, remote_hash) -> bool:
        """
        Synchronises local devices during connection phase.
        :param remote_hash: Hash stored on the platform.
        :return: Boolean.
        """
        devices = __class__.__device_manager.devices()
        if type(devices) is dict:
            devices = list(devices.values())
        local_hash = _hashDevices(devices)
        logger.debug('calculated local hash: {}'.format(local_hash))
        if not local_hash == remote_hash:
            logger.debug('local and remote hash differ: {} - {}'.format(local_hash, remote_hash))
            clr_msg = Message(handlers['clear_handler'])
            response = __class__.__send(clr_msg)
            if response.status == 200:
                for device in devices:
                    if not __class__.__put(device):
                        logger.error("synchronisation failed - device '{}' could not be synchronised".format(device.name))
                        return False
                if __class__.__commit(local_hash):
                    logger.info('synchronised devices')
                    return True
                logger.error("synchronisation failed - could not commit changes")
                return False
            else:
                logger.error("synchronisation could not be initiated - '{} {}'".format(response.payload, response.status))
                return False
        else:
            logger.debug('local and remote hash match')
        logger.info('devices already synchronised')
        return True


    @staticmethod
    def __send(msg_obj, timeout=10, callback=None, block=True) -> Message:
        """
        Send messages to the platform.
        :param msg_obj: Message object.
        :param timeout: Timeout in sec.
        :param callback: Method to be called on response or timeout.
        :param block: Boolean, set to False for asynchronous behavior.
        :return: Message object.
        """
        msg_str = marshalMsg(msg_obj)
        token = getMangledAttr(msg_obj, 'token')
        if block:
            event = Event()
            event.message = None
            callback = functools.partial(_callback, event)
            SessionManager.new(msg_obj, token, timeout, callback)
            __class__.__out_queue.put(msg_str)
            event.wait()
            return event.message
        else:
            SessionManager.new(msg_obj, token, timeout, callback)
            __class__.__out_queue.put(msg_str)


    @staticmethod
    def __commit(local_hash, **kwargs) -> bool:
        """
        Commits changes on the platform.
        :param local_hash: Hash calculated from devices provided via a device manager.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Boolean.
        """
        commit_msg = Message(handlers['commit_handler'])
        commit_msg.payload = local_hash
        response = __class__.__send(commit_msg, **kwargs)
        if response.status == 200:
            logger.debug("commit '{}'".format(local_hash))
            return True
        logger.debug("commit '{}' failed".format(local_hash))
        return False


    @staticmethod
    def __put(device, **kwargs) -> bool:
        """
        PUT a device to the platform. Commit required after call.
        :param device: Device (or subclass of Device) object.
        :param kwargs: timeout=10, callback=None, block=True.
        :return:
        """
        put_msg = Message(handlers['put_handler'])
        put_msg.payload = {
            'uri': device.id,
            'name': device.name,
            'iot_type': device.type,
            'tags': device.tags
        }
        response = __class__.__send(put_msg, **kwargs)
        if response.status == 200:
            logger.debug("put device '{}'".format(device.id))
            return True
        logger.debug("put device '{}' failed".format(device.id))
        return False


    @staticmethod
    def __disconnect(device_id, **kwargs) -> bool:
        """
        Disconnects a device from the platform. Commit required after call.
        :param device_id: Device ID as string.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Boolean.
        """
        discon_msg = Message(handlers['disconnect_handler'])
        discon_msg.payload = device_id
        response = __class__.__send(discon_msg, **kwargs)
        if response.status == 200:
            logger.debug("disconnect device '{}'".format(device_id))
            return True
        logger.debug("disconnect device '{}' failed".format(device_id))
        return False


    @staticmethod
    def __delete(device_id, **kwargs) -> bool:
        """
        Deletes a device from the platform. Commit required after call.
        :param device_id: Device ID as string.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Boolean.
        """
        del_msg = Message(handlers['delete_handler'])
        del_msg.payload = device_id
        response = __class__.__send(del_msg, **kwargs)
        if response.status == 200:
            logger.debug("delete device '{}'".format(device_id))
            return True
        logger.debug("delete device '{}' failed".format(device_id))
        return False


    #--------- User methods ---------#


    @staticmethod
    def event(device, service, data, metadata=None, **kwargs) -> Message:
        """
        User method for pushing events to the platform.
        :param device: Device ID or a Device (or subclass of Device) object.
        :param service: Device service.
        :param data: Event data as string.
        :param metadata: Event metadata.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Message object.
        """
        if _isDevice(device):
            d_id = device.id
        elif type(device) is str:
            d_id = device
        else:
            raise TypeError("device must be string, Device or subclass of Device but got '{}'".format(type(device)))
        if type(service) is not str:
            raise TypeError("service must be string but got '{}'".format(type(service)))
        event_msg = Message(handlers['event_handler'])
        event_msg.payload = {
            'device_uri': d_id,
            'service_uri': service,
            'value': [
                {
                    'name': 'metadata',
                    'value': metadata
                },
                {
                    'name': 'data',
                    'value': data
                }
            ]
        }
        if __class__.__ready:
            return __class__.__send(event_msg, **kwargs)
        logger.warning("could not send event: {}".format(event_msg.payload))


    @staticmethod
    def response(msg_obj, data, metadata=None, **kwargs):
        """
        User method for responding to a task / command from the platform.
        :param msg_obj: Original Message object from a task / command.
        :param data: Data concerning the completion of a task / command.
        :param metadata: Response metadata.
        :param kwargs: timeout=10, callback=None, block=True.
        """
        if type(msg_obj) is not Message:
            raise TypeError("msg_obj must be Message but got '{}'".format(type(msg_obj)))
        setMangledAttr(msg_obj, 'handler', handlers['response_handler'])
        msg_obj.payload['protocol_parts'] = [
            {
                'name': 'metadata',
                'value': metadata
            },
            {
                'name': 'data',
                'value': data
            }
        ]
        if __class__.__ready:
            __class__.__send(msg_obj, **kwargs)
        else:
            logger.warning("could not send response for: {}".format(getMangledAttr(msg_obj, 'token')))


    @staticmethod
    def add(device) -> bool:
        """
        User method for adding devices.
        :param device: Device (or subclass of Device) object.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Boolean.
        """
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        __class__.__device_manager.add(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__put(device):
                if __class__.__commit(local_hash):
                    logger.info("registered device '{}'".format(device.name))
                    return True
        logger.warning("could not register device '{}'".format(device.name))
        return False


    @staticmethod
    def update(device) -> bool:
        """
        User method for updating devices.
        :param device: Device (or subclass of Device) object.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Boolean.
        """
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        __class__.__device_manager.update(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__put(device):
                if __class__.__commit(local_hash):
                    logger.info("updated device '{}'".format(device.name))
                    return True
        logger.warning("could not update device '{}'".format(device.name))
        return False


    @staticmethod
    def disconnect(device) -> bool:
        """
        User method for disconnecting devices.
        :param device: Device ID or a Device (or subclass of Device) object.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Boolean.
        """
        if _isDevice(device):
            device = device.id
        elif type(device) is not str:
            raise TypeError("device must be Device, subclass of Device or string (if ID only) but got '{}'".format(type(device)))
        __class__.__device_manager.remove(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__disconnect(device):
                if __class__.__commit(local_hash):
                    logger.info("disconnected device '{}'".format(device))
                    return True
        logger.warning("could not disconnect device '{}'".format(device))
        return False


    @staticmethod
    def delete(device) -> bool:
        """
        User method for deleting devices.
        :param device: Device ID or a Device (or subclass of Device) object.
        :param kwargs: timeout=10, callback=None, block=True.
        :return: Boolean.
        """
        if _isDevice(device):
            device = device.id
        elif type(device) is not str:
            raise TypeError(
                "device must be Device, subclass of Device or string (if ID only) but got '{}'".format(type(device)))
        __class__.__device_manager.remove(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__delete(device):
                if __class__.__commit(local_hash):
                    logger.info("deleted device '{}'".format(device))
                    return True
        logger.warning("could not delete device '{}'".format(device))
        return False


    @staticmethod
    def receive() -> Message:
        """
        User method for receiving tasks / commands from the platform.
        :return: Message object.
        """
        return __class__.__client_queue.get()
