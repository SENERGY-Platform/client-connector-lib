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
    from connector.dm_interface import DeviceManagerInterface
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time, hashlib
from queue import Queue
from threading import Thread, Event

logger = root_logger.getChild(__name__)

logger.info(20 * '*' + ' Starting SEPL connector-client ' + 20 * '*')

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


def _callInThread(function):
    thread = Thread(target=function)
    thread.start()


class Client(metaclass=Singleton):
    __out_queue = Queue()
    __in_queue = Queue()
    __client_queue = Queue()
    __device_manager = None
    __ready = False


    def __init__(self, device_manager, con_callbck=None, discon_callbck=None):
        if not device_manager:
            raise RuntimeError("connector-client must be provided with a device manager")
        if not issubclass(device_manager, DeviceManagerInterface):
            raise TypeError("provided device manager must subclass DeviceManagerInterface")
        __class__.__device_manager = device_manager
        self.__con_callbck = con_callbck
        self.__discon_callbck = discon_callbck
        self.__session_manager = SessionManager()
        self.__callback_thread = Thread(target=self.__callbackHandler, name="Callback")
        self.__callback_thread.start()
        self.__router_thread = Thread(target=self.__router, name="Router")
        self.__router_thread.start()
        #self.__connect()


    def __reconnect(self):
        __class__.__ready = False
        if self.__discon_callbck:
            _callInThread(self.__discon_callbck)
        reconnect = Thread(target=self.__connect, name='reconnect', args=(30, ))
        logger.info("reconnecting in 30s")
        reconnect.start()

    '''   
    def __connect(self, wait=None):
        if wait:
            time.sleep(wait)
        websocket = Websocket(CONNECTOR_HOST, CONNECTOR_PORT, self.__reconnect)
        logger.info('trying to connect to SEPL connector')
        if _callAndWaitFor(websocket.connect):
            logger.info("connected to SEPL connector")
            logger.debug("starting handshake")
            credentials = {
                'user': CONNECTOR_USER,
                'pw': CONNECTOR_PASSWORD,
                'token': str(uuid())
            }
            logger.debug('sending credentials: {}'.format(credentials))
            if _callAndWaitFor(websocket.send, json.dumps(credentials)):
                answer = _callAndWaitFor(websocket.receive, timeout=10)
                if answer:
                    logger.debug('received answer: {}'.format(answer))
                    status, token, message = _parsePackage(answer)
                    if status == 'response' and token == credentials['token'] and message == 'ok':
                        logger.info('handshake completed')
                        _callAndWaitFor(websocket.ioStart, __class__.__in_queue, __class__.__out_queue)
                        __class__.__ready = True
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
        _callAndWaitFor(websocket.shutdown)
        return False
    '''

    def __connect(self, wait=None):
        if wait:
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
                    logger.debug('received initial message: {}'.format(initial_response))
                    intitial_response = unmarshalMsg(initial_response)
                    if intitial_response.status == 200 and getMangledAttr(intitial_response, 'token') == 'credentials':
                        logger.debug('check if gateay ID needs to be synchronised')
                        self.__synchroniseGid(intitial_response.payload.get('gid'))
                        logger.info('handshake completed')
                        _callAndWaitFor(websocket.ioStart, __class__.__in_queue, __class__.__out_queue)
                        logger.info('checking if devices need to be synchronised')
                        if self.__synchroniseDevices(intitial_response.payload.get('hash')):
                            logger.info('synchronised devices')
                            logger.info('connector-client ready')
                            if self.__con_callbck:
                                _callInThread(self.__con_callbck)
                            return True
                    else:
                        logger.error('handshake failed - {} {}'.format(intitial_response.payload, intitial_response.status))
                else:
                    logger.error('handshake failed - timed out')
            else:
                logger.error('could not initiate handshake')
        else:
            logger.error('could not connect')
        _callAndWaitFor(websocket.shutdown)
        return False


    def __synchroniseGid(self, remote_gid):
        if not CONNECTOR_GID == remote_gid:
            logger.debug('local and remote gateway ID differ: {} - {}'.format(CONNECTOR_GID, remote_gid))
            global CONNECTOR_GID
            CONNECTOR_GID = remote_gid
            writeConf(section='CONNECTOR', parameter='gid', value=remote_gid)
            logger.info("set gateway ID: '{}'".format(remote_gid))
        else:
            logger.debug('local and remote gateway ID match')


    def __hashDevices(self, devices):
        if type(devices) not in (dict, list, tuple):
            raise TypeError("please provide devices via dictionary, list or tuple - got '{}'".format(type(devices)))
        hashes = list()
        for device in devices:
            hashes.append(device.hash)
        hashes.sort()
        return hashlib.sha1(''.join(hashes).encode()).hexdigest()


    def __synchroniseDevices(self, remote_hash):
        dm = __class__.__device_manager()
        devices = dm.devices
        local_hash = self.__hashDevices(devices)
        logger.debug('calculated local hash: {}'.format(local_hash))
        if not local_hash == remote_hash:
            logger.debug('local and remote hash differ: {} - {}'.format(local_hash, remote_hash))
            clr_msg = Message(handlers['clear_handler'])
            response = __class__.__send(clr_msg)
            response = unmarshalMsg(response)
            if response.status == 200:
                for device in devices:
                    if not __class__.register(device):
                        logger.error("synchronisation failed - device could not be synchronised")
                        return False
                commit_msg = Message(handlers['commit_handler'])
                response = __class__.__send(commit_msg)
                if response.status == 200:
                    return True
                logger.error("synchronisation failed - could not commit changes")
                return False
            else:
                logger.error("synchronisation could not be initiated - '{} {}'".format(response.payload, response.status))
                return False
        else:
            logger.debug('local and remote hash match')
        return True


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


    @staticmethod
    def __send(msg_obj, timeout=10, callback=None, block=True) -> Message:
        if not __class__.__ready:
            logger.error("connector-client not ready")
        msg_str = marshalMsg(msg_obj)
        token = getMangledAttr(msg_obj, 'token')
        if block:
            event = Event()
            event.message = None
            callback = functools.partial(_callback, event)
            SessionManager.new(msg_obj, token, timeout, callback)
            __class__.__out_queue.put(msg_str)
            logger.debug('send: {}'.format(msg_str))
            event.wait()
            return event.message
        else:
            SessionManager.new(msg_obj, token, timeout, callback)
            __class__.__out_queue.put(msg_str)
            logger.debug('send: {}'.format(msg_str))


    #--------- User methods ---------#


    @staticmethod
    def event(device, service, payload, **kwargs) -> Message:
        if type(device) is Device:
            d_id = device.id
        elif type(device) is str:
            d_id = device
        else:
            raise TypeError("device must be string or Device but got '{}'".format(type(device)))
        if type(service) is not str:
            raise TypeError("service must be string but got '{}'".format(type(service)))
        #if type(payload) is not str:
        #    raise TypeError("payload must be string but got '{}'".format(type(payload)))
        msg = {
            'device_uri': d_id,
            'service_uri': service,
            'value': [
                {
                    'name': 'body',
                    'value': payload
                }
            ]
        }
        msg_obj = Message(handler=handlers['event_handler'])
        msg_obj.payload = msg
        return __class__.__send(msg_obj, **kwargs)


    @staticmethod
    def response(msg_obj, payload, **kwargs):
        if type(msg_obj) is not Message:
            raise TypeError("msg_obj must be Message but got '{}'".format(type(msg_obj)))
        # if type(payload) is not str:
        #    raise TypeError("payload must be string but got '{}'".format(type(payload)))
        setMangledAttr(msg_obj, 'handler', handlers['response_handler'])
        msg_obj.payload['protocol_parts'] = [
            {
                'name': 'body',
                'value': payload
            }
        ]
        return __class__.__send(msg_obj, **kwargs) ######### Ingo Fragen oder vllt Fehler im Session Manager?


    @staticmethod
    def register(device) -> bool:
        if type(device) is not Device:
            raise TypeError("register takes a 'Device' object but got '{}'".format(type(device)))
        dm = __class__.__device_manager()
        dm.add(device)
        put_msg = Message(handlers['put_handler'])
        put_msg.payload = {
            'uri': device.id,
            'name': device.name,
            'tags': device.tags
        }
        response = __class__.__send(put_msg)
        if response.status == 200:
            logger.info("registered device '{}'".format(device.name))
            return True
        logger.warning("could not register device '{}'".format(device.name))
        return False







    @staticmethod
    def receive() -> Message:
        return __class__.__client_queue.get()


    '''
    @staticmethod
    def update(device) -> bool:
        if type(device) is not Device:
            raise TypeError("update takes a 'Device' object but got '{}'".format(type(device)))
        dm = __class__.__device_manager()
        dm.update(device)
        response = __class__.send(_UpdateName(device))
        response2 = __class__.send(_UpdateTags(device))
        if type(response) is Response and type(response2) is Response:
            logger.info("updated device '{}'".format(device.name))
            return True
        logger.warning("could not update device '{}'".format(device.name))
        return False
    '''
