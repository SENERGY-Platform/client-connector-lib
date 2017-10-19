if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from modules.http_lib import Methods as http
    from connector.configuration import CONNECTOR_USER, CONNECTOR_PASSWORD, CONNECTOR_HOST, CONNECTOR_PORT, CONNECTOR_GID, writeConf
    from connector.session import SessionManager
    from connector.websocket import Websocket
    from connector.message import Message, handlers, marshalMsg, unmarshalMsg, getMangledAttr, setMangledAttr
    from connector.device import DeviceManagerInterface, Device, _isDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time, hashlib
from queue import Queue
from threading import Thread, Event
from inspect import isclass

logger = root_logger.getChild(__name__)

logger.info(20 * '*' + ' Starting SEPL connector-client ' + 20 * '*')


def _callback(event, message=None):
    event.message = message
    event.set()


def _callAndWaitFor(function, *args, timeout=None, **kwargs):
    event = Event()
    event.message = None
    function(functools.partial(_callback, event), *args, **kwargs)
    event.wait(timeout=timeout)
    return event.message


def _interfaceCheck(cls, interface):
    if issubclass(cls, interface):
        return True
    raise TypeError("provided class '{}' must be a subclass of '{}'".format(cls, interface))


def _synchroniseGid(remote_gid):
    global CONNECTOR_GID
    if not CONNECTOR_GID == remote_gid:
        logger.debug('local and remote gateway ID differ: {} - {}'.format(CONNECTOR_GID, remote_gid))
        CONNECTOR_GID = remote_gid
        writeConf(section='CONNECTOR', option='gid', value=remote_gid)
        logger.info("set gateway ID: '{}'".format(remote_gid))
    else:
        logger.debug('local and remote gateway ID match')


def _hashDevices(devices) -> str:
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
    __out_queue = Queue()
    __in_queue = Queue()
    __client_queue = Queue()
    __device_manager = None
    __ready = False


    def __init__(self, device_manager, con_callbck=None, discon_callbck=None):
        if not device_manager:
            raise RuntimeError("a device manager must be provided")
        elif isclass(device_manager):
            if not _interfaceCheck(device_manager, DeviceManagerInterface):
                raise TypeError("device manager must subclass DeviceManagerInterface but got {}".format(device_manager))
        elif not _interfaceCheck(type(device_manager), DeviceManagerInterface):
            raise TypeError("device manager must subclass DeviceManagerInterface but got {}".format(type(device_manager)))
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
        while True:
            callback, msg_obj = SessionManager.callback_queue.get()
            callback(msg_obj)


    def __router(self):
        while True:
            msg_str = __class__.__in_queue.get()
            msg_obj = unmarshalMsg(msg_str)
            if msg_obj:
                if getMangledAttr(msg_obj, 'handler') == handlers['command_handler']:
                    __class__.__client_queue.put(msg_obj)
                else:
                    SessionManager.raiseEvent(msg_obj, getMangledAttr(msg_obj, 'token'))


    def __connect(self, wait=None) -> bool:
        if wait:
            if self.__discon_callbck:
                self.__discon_callbck()
            time.sleep(wait)
        credentials = json.dumps({
            'user': CONNECTOR_USER,
            'pw': CONNECTOR_PASSWORD,
            'gid': CONNECTOR_GID,
            'token': 'credentials'
        })
        websocket = Websocket(CONNECTOR_HOST, CONNECTOR_PORT, self.__reconnect)
        logger.info('trying to connect to SEPL connector')
        if _callAndWaitFor(websocket.connect):
            logger.info("connected to SEPL connector")
            logger.debug("starting handshake")
            logger.debug('sending credentials: {}'.format(credentials))
            if _callAndWaitFor(websocket.send, credentials):
                initial_response = _callAndWaitFor(websocket.receive, timeout=10)
                if initial_response:
                    logger.debug('received initial response: {}'.format(initial_response))
                    initial_response = unmarshalMsg(initial_response)
                    if initial_response and initial_response.status == 200 and getMangledAttr(initial_response, 'token') == 'credentials':
                        logger.debug('check if gateay ID needs to be synchronised')
                        _synchroniseGid(initial_response.payload.get('gid'))
                        logger.info('handshake completed')
                        __class__.__out_queue.empty()
                        _callAndWaitFor(websocket.ioStart, __class__.__in_queue, __class__.__out_queue)
                        logger.info('checking if devices need to be synchronised')
                        if self.__synchroniseDevices(initial_response.payload.get('hash')):
                            logger.info('connector-client ready')
                            __class__.__ready = True
                            if self.__con_callbck:
                                self.__con_callbck()
                            return True
                    else:
                        logger.error('handshake failed - {} {}'.format(initial_response.payload, initial_response.status))
                else:
                    logger.error('handshake failed - timed out')
            else:
                logger.error('could not initiate handshake')
        else:
            logger.error('could not connect')
        _callAndWaitFor(websocket.shutdown)
        return False


    def __reconnect(self):
        __class__.__ready = False
        reconnect = Thread(target=self.__connect, name='reconnect', args=(30, ))
        logger.info("reconnecting in 30s")
        reconnect.start()


    def __synchroniseDevices(self, remote_hash) -> bool:
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
            __class__.__out_queue.put((msg_str, functools.partial(SessionManager.new, msg_obj, token, timeout, callback)))


    @staticmethod
    def __put(device, **kwargs) -> bool:
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
    def __commit(local_hash, **kwargs) -> bool:
        commit_msg = Message(handlers['commit_handler'])
        commit_msg.payload = local_hash
        response = __class__.__send(commit_msg, **kwargs)
        if response.status == 200:
            logger.debug("commit '{}'".format(local_hash))
            return True
        logger.debug("commit '{}' failed".format(local_hash))
        return False


    @staticmethod
    def __disconnect(device_id, **kwargs) -> bool:
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
    def event(device, service, payload, **kwargs) -> Message:
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
                    'name': 'body',
                    'value': payload
                }
            ]
        }
        if __class__.__ready:
            return __class__.__send(event_msg, **kwargs)
        logger.warning("could not send event: {}".format(event_msg.payload))


    @staticmethod
    def response(msg_obj, payload, **kwargs):
        if type(msg_obj) is not Message:
            raise TypeError("msg_obj must be Message but got '{}'".format(type(msg_obj)))
        setMangledAttr(msg_obj, 'handler', handlers['response_handler'])
        msg_obj.payload['protocol_parts'] = [
            {
                'name': 'body',
                'value': payload
            }
        ]
        if __class__.__ready:
            __class__.__send(msg_obj, **kwargs)
        else:
            logger.warning("could not send response for: {}".format(getMangledAttr(msg_obj, 'token')))


    @staticmethod
    def add(device, **kwargs) -> bool:
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        __class__.__device_manager.add(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__put(device, **kwargs):
                if __class__.__commit(local_hash):
                    logger.info("registered device '{}'".format(device.name))
                    return True
        logger.warning("could not register device '{}'".format(device.name))
        return False


    @staticmethod
    def update(device, **kwargs) -> bool:
        if not _isDevice(device):
            raise TypeError("device must be Device or subclass of Device but got '{}'".format(type(device)))
        __class__.__device_manager.update(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__put(device, **kwargs):
                if __class__.__commit(local_hash):
                    logger.info("updated device '{}'".format(device.name))
                    return True
        logger.warning("could not update device '{}'".format(device.name))
        return False


    @staticmethod
    def disconnect(device, **kwargs) -> bool:
        if _isDevice(device):
            device = device.id
        elif type(device) is not str:
            raise TypeError("device must be Device, subclass of Device or string (if ID only) but got '{}'".format(type(device)))
        __class__.__device_manager.remove(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__disconnect(device, **kwargs):
                if __class__.__commit(local_hash):
                    logger.info("disconnected device '{}'".format(device))
                    return True
        logger.warning("could not disconnect device '{}'".format(device))
        return False


    @staticmethod
    def delete(device, **kwargs) -> bool:
        if _isDevice(device):
            device = device.id
        elif type(device) is not str:
            raise TypeError(
                "device must be Device, subclass of Device or string (if ID only) but got '{}'".format(type(device)))
        __class__.__device_manager.remove(device)
        if __class__.__ready:
            local_hash = _hashDevices(__class__.__device_manager.devices())
            if __class__.__delete(device, **kwargs):
                if __class__.__commit(local_hash):
                    logger.info("deleted device '{}'".format(device))
                    return True
        logger.warning("could not delete device '{}'".format(device))
        return False


    @staticmethod
    def receive() -> Message:
        return __class__.__client_queue.get()
