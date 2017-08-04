if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from modules.http_lib import Methods as http
    from connector.configuration import CONNECTOR_LOOKUP_URL, CONNECTOR_USER, CONNECTOR_PASSWORD, CONNECTOR_DEVICE_REGISTRATION_PATH
    from connector.websocket import Websocket
    from connector.message import Message, Prefix
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time
from queue import Queue, Empty
from threading import Thread, Event

logger = root_logger.getChild(__name__)


OUT_QUEUE = Queue()
IN_QUEUE = Queue()


def callback(event, message=None):
    event.message = message
    event.set()

def callAndWaitFor(function, *args, timeout=None):
    event = Event()
    event.message = None
    function(functools.partial(callback, event), *args)
    event.wait(timeout=timeout)
    return event.message

class Connector(Thread, metaclass=Singleton):
    _host = str()
    _http_port = int()
    _ws_port = int()

    def __init__(self, con_callbck=None, discon_callbck=None):
        super().__init__()
        self._con_callbck = con_callbck
        self._discon_callbck = discon_callbck
        self.start()

    def _lookup(self):
        response = http.get(CONNECTOR_LOOKUP_URL)
        if response.status == 200:
            Connector._host = response.body.split("ws://")[1].split(":")[0]
            Connector._ws_port = response.body.split("ws://")[1].split(":")[1]
            Connector._http_port = response.body.split("ws://")[1].split(":")[1]
            return True
        else:
            logger.error("lookup failed - '{}'".format(response.status))
            return False

    def _checkAndCall(self, function):
        if function:
            function()

    def run(self):
        logger.info(20*'*'+' Starting SEPL connector client '+20*'*')
        while True:
            while not self._lookup():
                logger.debug("retry in 10s")
                time.sleep(10)
            websocket = Websocket(IN_QUEUE, OUT_QUEUE, Connector._host, Connector._ws_port)
            if callAndWaitFor(websocket.connect):
                logger.info("sending credentials")
                if callAndWaitFor(websocket.send, json.dumps(self._credentials)):
                    answer = callAndWaitFor(websocket.receive, timeout=10)
                    if answer:
                        logger.info("received answer")
                        logger.debug(answer)
                        callAndWaitFor(websocket.ioStart)
                        self._checkAndCall(self._con_callbck)
                        websocket.join()
                        self._checkAndCall(self._discon_callbck)
                    else:
                        logger.info("no answer")
                        callAndWaitFor(websocket.shutdown)
                        websocket.join()
            else:
                callAndWaitFor(websocket.shutdown)
                websocket.join()
            logger.info("reconnecting in 30s")
            time.sleep(30)

    @staticmethod
    def send(message, callback, timeout=10, retries=0, retry_delay=0.5):
        msg_str = Message.pack(message)
        OUT_QUEUE.put(msg_str)

    @staticmethod
    def receive():
        while True:
            try:
                message = IN_QUEUE.get(timeout=2)
                return Message.unpack(message)
            except Empty:
                pass

    @staticmethod
    def register(devices):
        pass

    @staticmethod
    def unregister(devices):
        pass
