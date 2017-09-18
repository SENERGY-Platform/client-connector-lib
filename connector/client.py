if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from modules.http_lib import Methods as http
    from connector.configuration import CONNECTOR_USER, CONNECTOR_PASSWORD, CONNECTOR_HOST, CONNECTOR_PORT
    from connector.session import SessionManager
    from connector.websocket import Websocket
    from connector.message.client import _client_msg_prefix, _Remove, _Mute, _UpdateName, _UpdateTags, _Add, _Listen
    from connector.message.connector import Command, Response, connector_msg_obj
    from connector.device import Device, DevicePool
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time
from queue import Queue
from threading import Thread, Event
from uuid import uuid4 as uuid


logger = root_logger.getChild(__name__)

logger.info(10 * '*' + ' Starting SEPL connector-client ' + 10 * '*')

OUT_QUEUE = Queue()
IN_QUEUE = Queue()


def _callback(event, message=None):
    event.message = message
    event.set()


def _callAndWaitFor(function, *args, timeout=None, **kwargs):
    event = Event()
    event.message = None
    function(functools.partial(_callback, event), *args, **kwargs)
    event.wait(timeout=timeout)
    return event.message


def _parsePackage(package):
    try:
        handler_and_token, message = package.split(':', maxsplit=1)
        #### temp ####
        if '.' in handler_and_token:
            handler, token = handler_and_token.split('.', maxsplit=1)
        else:
            handler = handler_and_token
            token = str(uuid())
        #### temp ####
        return handler, token, message
    except ValueError:
        logger.error('malformed package: {}'.format(package))
        return False


def _createPackage(msg_obj):
    return '{}.{}:{}'.format(
        _client_msg_prefix.get(type(msg_obj)),
        msg_obj._token,
        msg_obj.__class__._serialize(msg_obj)
    )


def _callInThread(function):
    thread = Thread(target=function)
    thread.start()


class Client(metaclass=Singleton):
    __out_queue = Queue()
    __in_queue = Queue()
    __client_queue = Queue()


    def __init__(self, con_callbck=None, discon_callbck=None):
        self.__con_callbck = con_callbck
        self.__discon_callbck = discon_callbck
        self.__websocket = None
        self.__callback_thread = Thread(target=self.__callbackHandler, name="Callback")
        self.__session_manager_thread = SessionManager()
        self.__router_thread = Thread(target=self.__router, name="Router")
        self.__callback_thread.start()
        self.__session_manager_thread.start()
        self.__router_thread.start()
        #self.__connect()


    def __reconnect(self):
        if self.__discon_callbck:
            _callInThread(self.__discon_callbck)
        self.__websocket = None
        reconnect = Thread(target=self.__connect, name='reconnect', args=(30, ))
        logger.info("reconnecting in 30s")
        reconnect.start()


    def __listenAllDevices(self):
        devices = DevicePool.dump()
        logger.debug('fetched devices from pool: {}'.format(devices))
        if devices:
            id_list = [device.id for device in devices.values()]
            logger.info('checking known devices')
            msg_objs= list()
            batch_size = 4
            for x in range(0, len(id_list), batch_size):
                msg_objs.append(_Listen(None, id_list[x:x+batch_size]))
            count = 0
            for obj in msg_objs:
                response = __class__.send(obj)
                if type(response) is Response:
                    count = count + 1
                    unused = json.loads(response.payload.body).get('unused')
                    if unused:
                        for d_id in unused:
                            logger.debug("registering unused device ‘{}‘".format(d_id))
                            __class__.register(devices[d_id])
            if count == len(msg_objs):
                return True
            else:
                return False
        else:
            return True


    def __connect(self, wait=None):
        if wait:
            time.sleep(wait)
        self.__websocket = Websocket(CONNECTOR_HOST, CONNECTOR_PORT, self.__reconnect)
        logger.info('trying to connect to SEPL connector')
        if _callAndWaitFor(self.__websocket.connect):
            logger.info("connected to SEPL connector")
            logger.debug("starting handshake")
            credentials = {
                'user': CONNECTOR_USER,
                'pw': CONNECTOR_PASSWORD,
                'token': str(uuid())
            }
            logger.debug('sending credentials: {}'.format(credentials))
            if _callAndWaitFor(self.__websocket.send, json.dumps(credentials)):
                answer = _callAndWaitFor(self.__websocket.receive, timeout=10)
                if answer:
                    logger.debug('received answer: {}'.format(answer))
                    status, token, message = _parsePackage(answer)
                    if status == 'response' and token == credentials['token'] and message == 'ok':
                        logger.info('handshake completed')
                        _callAndWaitFor(self.__websocket.ioStart, __class__.__in_queue, __class__.__out_queue)
                        if self.__listenAllDevices():
                            logger.info('connector-client ready')
                            if self.__con_callbck:
                                _callInThread(self.__con_callbck)
                            return True
                        else:
                            logger.error('could not register known devices')
                    else:
                        logger.error('handshake failed')
                else:
                    logger.error('handshake timed out')
            else:
                logger.error('could not initiate handshake')
        else:
            logger.error('could not connect')
        _callAndWaitFor(self.__websocket.shutdown)
        self.__websocket = None
        return False


    def __callbackHandler(self):
        while True:
            callback, msg_obj = SessionManager.callback_queue.get()
            callback(msg_obj)


    def __router(self):
        while True:
            package = __class__.__in_queue.get()
            if package:
                prefix, token, message = _parsePackage(package)
                msg_obj = connector_msg_obj.get(prefix)(message)
                msg_obj._token = token
                if type(msg_obj) is Command:
                    __class__.__client_queue.put(msg_obj)
                else:
                    SessionManager.raiseEvent(msg_obj)


    @staticmethod
    def __send(msg_obj, timeout, retries, callback):
        if not msg_obj._token:
            msg_obj._token = str(uuid())
        package = _createPackage(msg_obj)
        SessionManager.new(msg_obj, timeout, retries, callback)
        __class__.__out_queue.put(package)
        logger.debug('send: {}'.format(package))



    #--------- User methods ---------#


    def init(self, devices=None):
        if devices:
            if type(devices) is not list:
                raise TypeError("Device objects must be provided in a list but got '{}'".format(type(devices)))
            for device in devices:
                DevicePool.add(device)
        self.__connect()


    @staticmethod
    def send(msg_obj, timeout=10, retries=0, callback=None, block=True):
        if type(msg_obj) not in _client_msg_prefix.keys():
            raise TypeError("message must be either 'Response' or 'Event' but got '{}'".format(type(msg_obj)))
        if block:
            event = Event()
            event.message = None
            callback = functools.partial(_callback, event)
            __class__.__send(msg_obj, timeout, retries, callback)
            event.wait()
            return event.message
        else:
            __class__.__send(msg_obj, timeout, retries, callback)


    @staticmethod
    def receive() -> Command:
        return __class__.__client_queue.get()


    @staticmethod
    def register(device) -> bool:
        if type(device) is not Device:
            raise TypeError("register takes a 'Device' object but got '{}'".format(type(device)))
        DevicePool.add(device)
        response = __class__.send(_Listen(device))
        if type(response) is Response:
            response = json.loads(response.payload.body)
            if response.get('unused'):
                response = __class__.send(_Add(device))
                if type(response) is Response:
                    response = __class__.send(_Listen(device))
                    if type(response) is Response:
                        response = json.loads(response.payload.body)
                        if response.get('used'):
                            logger.info("registered device '{}'".format(device.name))
                            return True
                    logger.warning("could not register device '{}'".format(device.name))
                    return False
            logger.info("device '{}' already registered".format(device.name))
            return True
        logger.warning("could not register device '{}'".format(device.name))
        return False


    @staticmethod
    def update(device) -> bool:
        if type(device) is not Device:
            raise TypeError("update takes a 'Device' object but got '{}'".format(type(device)))
        DevicePool.update(device)
        response = __class__.send(_UpdateName(device))
        response2 = __class__.send(_UpdateTags(device))
        if type(response) is Response and type(response2) is Response:
            logger.info("updated device '{}'".format(device.name))
            return True
        logger.warning("could not update device '{}'".format(device.name))
        return False


    '''
    @staticmethod
    def deregisterDevice(device) -> bool:
        if type(device) is Device:
            d_id = device.id
        elif type(device) is str:
            d_id = device
        else:
            raise TypeError("a string or a Device object must be provided but got a '{}'".format(type(device)))
        DevicePool.remove(d_id)
    
    @staticmethod
    def muteDevice(device) -> bool:
        if type(device) is not Device:
            raise TypeError("mute takes a 'Device' object but got '{}'".format(type(device)))

    @staticmethod
    def getDevice(id) -> Device:
        device_manager = DeviceManager()
        return device_manager.get(id)

    @staticmethod
    def getAllDevices() -> dict:
        device_manager = DeviceManager()
        return device_manager.getAll()
    '''
