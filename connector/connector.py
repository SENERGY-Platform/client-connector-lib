if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from modules.http_lib import Methods as http
    from connector.configuration import CONNECTOR_LOOKUP_URL, CONNECTOR_USER, CONNECTOR_PASSWORD, CONNECTOR_DEVICE_REGISTRATION_PATH
    from connector.websocket import Websocket
    from connector.message import Message, serializeMessage, deserializeMessage
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time
from queue import Queue, Empty
from threading import Thread, Event
from uuid import uuid4 as uuid

logger = root_logger.getChild(__name__)



def callback(event, message=None):
    event.message = message
    event.set()

def callAndWaitFor(function, *args, timeout=None):
    event = Event()
    event.message = None
    function(functools.partial(callback, event), *args)
    event.wait(timeout=timeout)
    return event.message

def checkAndCall(function):
    if function:
        function()

class Connector(metaclass=Singleton):
    __host = str()
    __http_port = int()
    __ws_port = int()
    __out_queue = Queue()
    __in_queue = Queue()
    __user_queue = Queue()


    def __init__(self, con_callbck=None, discon_callbck=None):
        self.__con_callbck = con_callbck
        self.__discon_callbck = discon_callbck
        self.__websocket = None
        self.__router_thread = Thread(target=self.__router, name="Router")
        self.__connect_thread = Thread(target=self.__connect(), name="Connect")
        self.__router_thread.start()
        self.__connect_thread.start()


    def __lookup(self):
        response = http.get(CONNECTOR_LOOKUP_URL)
        if response.status == 200:
            __class__.__host = response.body.split("ws://")[1].split(":")[0]
            __class__.__ws_port = response.body.split("ws://")[1].split(":")[1]
            __class__.__http_port = response.body.split("ws://")[1].split(":")[1]
            return True
        else:
            logger.debug("lookup status - '{}'".format(response.status))
            return False


    def __reconnect(self):
        checkAndCall(self.__discon_callbck)
        self.__websocket = None
        reconnect = Thread(target=self.__connect, name='reconnect', args=(30, ))
        reconnect.start()
        logger.info("reconnecting in 30s")


    def __connect(self, wait=None):
        if wait:
            time.sleep(wait)
        logger.info('looking for SEPL connector')
        while not self.__lookup():
            logger.error('lookup failed')
            time.sleep(10)
        self.__websocket = Websocket(__class__.__host, __class__.__ws_port, self.__reconnect())
        logger.info('connecting to SEPL connector')
        if callAndWaitFor(self.__websocket.connect):
            logger.info("preparing handshake")
            credentials = {
                'user': CONNECTOR_USER,
                'pw': CONNECTOR_PASSWORD,
                'token': uuid()
            }
            logger.debug(credentials)
            logger.info('sending credentials')
            if callAndWaitFor(self.__websocket.send, json.dumps(credentials)):
                answer = callAndWaitFor(self.__websocket.receive, timeout=10)
                if answer:
                    logger.info('received answer')
                    logger.debug(answer)
                    status, token, message = __class__.__parsePackage(answer)
                    if status is 'response' and token is credentials['token']:
                        logger.info('handshake completed')
                        callAndWaitFor(self.__websocket.ioStart, __class__.__in_queue, __class__.__out_queue)
                        checkAndCall(self.__con_callbck)
                        return True
                    else:
                        logger.error('handshake failed')
                else:
                    logger.error('handshake timed out')
            else:
                logger.error('could start handshake')
        else:
            logger.error('could not connect')
        callAndWaitFor(self.__websocket.shutdown)
        self.__websocket = None
        return False





    def __router(self):
        logger.info(20 * '*' + ' Starting SEPL connector client ' + 20 * '*')
        while True:
            package = __class__.__in_queue.get()
            handler, token, message = __class__.__parsePackage(package)








    @staticmethod
    def __parsePackage(package):
        handler_and_token, message = package.split(':', maxsplit=1)
        #### temp ####
        if '.' in handler_and_token:
            handler, token = handler_and_token.split('.', maxsplit=1)
        else:
            handler = handler_and_token
            token = uuid()
        #### temp ####
        return handler, token, message

    @staticmethod
    def __createPackage(handler, token, message):
        return '{}.{}:{}'.format(handler, token, message)

    @staticmethod
    def __send(handler, token, message, timeout, callback):
        package = __class__.__createPackage(handler, token, message)
        #TokenManager.add(token, package, callback, timeout)
        print(package)





    @staticmethod
    def send(message: Message, timeout=10, callback=None):
        if message._Message__token:
            __class__.__send('response', message._Message__token, serializeMessage(message), timeout, callback)
        else:
            __class__.__send('event', uuid(), serializeMessage(message), timeout, callback)

    @staticmethod
    def receive() -> Message:
        while True:
            try:
                package = __class__.__user_queue.get(timeout=2)
                handler, token, message = __class__.__parsePackage(package)
                message = deserializeMessage(message)
                message._Message__token = token
                return message
            except Empty:
                pass

    @staticmethod
    def register(devices):
        pass

    @staticmethod
    def unregister(devices):
        pass
