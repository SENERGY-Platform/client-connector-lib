if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from modules.http_lib import Methods as http
    from connector.configuration import CONNECTOR_USER, CONNECTOR_PASSWORD, CONNECTOR_HOST, CONNECTOR_PORT
    from connector.session import SessionManager
    from connector.websocket import Websocket
    from connector.message import ConnectorMsg, ClientMsg
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time
from queue import Queue
from threading import Thread, Event


logger = root_logger.getChild(__name__)


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


def _checkAndCall(function):
    if function:
        function()


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
    except Exception:
        return None


def _createPackage(handler, token, message):
    return '{}.{}:{}'.format(handler, token, message)


class Connector(metaclass=Singleton):
    __out_queue = Queue()
    __in_queue = Queue()
    __user_queue = Queue()


    def __init__(self, con_callbck=None, discon_callbck=None):
        logger.info(10 * '*' + ' Starting SEPL connector client ' + 10 * '*')
        self.__con_callbck = con_callbck
        self.__discon_callbck = discon_callbck
        self.__websocket = None
        self.__callback_thread = Thread(target=self.__callbackHandler, name="Callback")
        self.__session_manager_thread = SessionManager()
        self.__router_thread = Thread(target=self.__router, name="Router")
        self.__connect_thread = Thread(target=self.__connect, name="Connect")
        self.__callback_thread.start()
        self.__session_manager_thread.start()
        #self.__router_thread.start()
        #self.__connect_thread.start()


    def __reconnect(self):
        logger.warning('disconnected')
        _checkAndCall(self.__discon_callbck)
        self.__websocket = None
        reconnect = Thread(target=self.__connect, name='reconnect', args=(30, ))
        logger.info("reconnecting in 30s")
        reconnect.start()


    def __connect(self, wait=None):
        if wait:
            time.sleep(wait)
        self.__websocket = Websocket(CONNECTOR_HOST, CONNECTOR_PORT, self.__reconnect)
        logger.info('connecting to SEPL connector')
        if _callAndWaitFor(self.__websocket.connect):
            logger.info("connection established")
            logger.info("preparing handshake")
            credentials = {
                'user': CONNECTOR_USER,
                'pw': CONNECTOR_PASSWORD,
                'token': str(uuid())
            }
            logger.debug(credentials)
            logger.info('sending credentials')
            if _callAndWaitFor(self.__websocket.send, json.dumps(credentials)):
                answer = _callAndWaitFor(self.__websocket.receive, timeout=10)
                if answer:
                    logger.info('received answer')
                    logger.debug(answer)
                    status, token, message = _parsePackage(answer)
                    if status == 'response' and token == credentials['token'] and message == 'ok':
                        logger.info('handshake completed')
                        _callAndWaitFor(self.__websocket.ioStart, __class__.__in_queue, __class__.__out_queue)
                        logger.info('connector client ready')
                        _checkAndCall(self.__con_callbck)
                        return True
                    else:
                        logger.error('handshake failed')
                else:
                    logger.error('handshake timed out')
            else:
                logger.error('could not start handshake')
        else:
            logger.error('could not connect')
        _callAndWaitFor(self.__websocket.shutdown)
        self.__websocket = None
        return False



    def __callbackHandler(self):
        while True:
            callback = SessionManager.callback_queue.get()
            callback()



    def __router(self):
        while True:
            package = __class__.__in_queue.get()
            if package:
                handler, token, message = _parsePackage(package)
                if handler == 'command':
                    message = ConnectorMsg.Command(message)
                    message._token = token
                    __class__.__user_queue.put(message)
                elif handler == 'error' or handler == 'response':
                    SessionManager.raiseEvent(token)











    @staticmethod
    def __send(message, timeout, retries, callback):
        package = _createPackage(handler, token, message)
        SessionManager.new(token, timeout, callback)
        logger.debug('send: {}'.format(package))





    #--------- User methods ---------#


    @staticmethod
    def send(message, timeout=10, retries=0, callback=None, block=False):
        if type(message) not in ClientMsg.__dict__.values():
            raise TypeError("message must be either ClientMsg.Response or ClientMsg.Event but got '{}'".format(type(message)))
        if block:
            event = Event()
            event.message = None
            callback = functools.partial(_callback, event)
            __class__.__send(message, timeout, retries, callback)
            event.wait()
        else:
            __class__.__send(message, timeout, retries, callback)


    __handlers = {
        'command': ConnectorMsg.Command,
        'response': ConnectorMsg.Response,
        'error': ConnectorMsg.Error
    }

    @staticmethod
    def receive():
        package = __class__.__in_queue.get()
        if package:
            handler, token, message = _parsePackage(package)
            msg_obj = __class__.__handlers.get(handler)(message)
            msg_obj._token = token
            if handler == 'command':
                message = ConnectorMsg.Command(message)
                message._token = token
                __class__.__user_queue.put(message)
            elif handler == 'error' or handler == 'response':
                SessionManager.raiseEvent(token)





    # --------- Tests ---------#

    @staticmethod
    def testPutIn(package):
        __class__.__in_queue.put(package)