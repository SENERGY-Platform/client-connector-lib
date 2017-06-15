if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.http_lib import Methods as http
    from connector.configuration import CONNECTOR_LOOKUP_URL, CONNECTOR_USER, CONNECTOR_PASSWORD, CONNECTOR_DEVICE_REGISTRATION_PATH
    from connector.websocket import Websocket
    from connector.message import Message
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, json, time
from queue import Queue, Empty
from threading import Thread, Event

logger = root_logger.getChild(__name__)


OUT_QUEUE = Queue()
IN_QUEUE = Queue()

class Connector(Thread):
    _host = str()
    _http_port = int()
    _ws_port = int()
    _ws_open = False

    def __init__(self, con_callbck=None, discon_callbck=None):
        super().__init__()
        self._con_callbck = con_callbck
        self._discon_callbck = discon_callbck
        self._credentials = {'user': CONNECTOR_USER, 'pw': CONNECTOR_PASSWORD}
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

    def _callback(self, event, message=None):
        event.message = message
        event.set()

    def _callAndWaitFor(self, function, *args, timeout=None):
        event = Event()
        event.message = None
        callback = functools.partial(self._callback, event)
        function(callback, *args)
        event.wait(timeout=timeout)
        return event.message

    def _checkAndCall(self, function):
        if function:
            function()

    def run(self):
        while True:
            while not self._lookup():
                logger.debug("retry in 10s")
                time.sleep(10)
            websocket = Websocket(IN_QUEUE, OUT_QUEUE, Connector._host, Connector._ws_port)
            if self._callAndWaitFor(websocket.connect):
                logger.info("sending credentials")
                if self._callAndWaitFor(websocket.send, json.dumps(self._credentials)):
                    answer = True #self._call_and_wait_for(websocket.receive, timeout=10)
                    if answer:
                        #logger.info("received answer")
                        #logger.debug(answer)
                        self._callAndWaitFor(websocket.ioStart)
                        Connector._ws_open = True
                        self._checkAndCall(self._con_callbck)
                        websocket.join()
                        Connector._ws_open = False
                        self._checkAndCall(self._discon_callbck)
                    else:
                        logger.info("no answer")
                        self._callAndWaitFor(websocket.shutdown)
                        websocket.join()
            else:
                self._callAndWaitFor(websocket.shutdown)
                websocket.join()
            logger.info("reconnecting in 30s")
            time.sleep(30)

    @staticmethod
    def send(message):
        if type(message) is Message:                # temp workaround
            OUT_QUEUE.put(Message.pack(message))
        else:
            OUT_QUEUE.put(message)

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
        if type(devices) is not list:
            devices = [devices]
        payload = {
            "credentials": {
                "user": CONNECTOR_USER,
                "pw": CONNECTOR_PASSWORD
            },
            "devices": [
                {
                "id": device.id,
                "zway_type": device.type,
                "title": device.name
                }
                for device in devices
            ]
        }
        response = http.post(
            'http://{}:{}/{}'.format(
                Connector._host,
                Connector._http_port,
                CONNECTOR_DEVICE_REGISTRATION_PATH
            ),
            json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=30 # reduce in future
        )
        if response.status == 200:
            message = Message()
            message._payload = 'update'
            Connector.send(message)
            logger.info("registered devices with platform")
            return True
        else:
            logger.error("could not register devices - '{}'".format(response.status))
            return False

    @staticmethod
    def unregister(devices):
        if type(devices) is not list:
            devices = [devices]
        # ask Ingo
        """response = http.delete(
            'http://{}:{}/{}/{}'.format(
                Connector._host,
                Connector._http_port,
                CONNECTOR_DEVICE_REGISTRATION_PATH,
                device.id
            )
        )"""
