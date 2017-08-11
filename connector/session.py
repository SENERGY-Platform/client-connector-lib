if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, asyncio, concurrent.futures
from threading import Thread
from queue import Queue

logger = root_logger.getChild(__name__)


class TestDict(dict):
    def __init__(self):
        super().__init__()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        logger.info('key {} and value {}'.format(key, value))


class Session:
    def __init__(self, token, timeout, callback):
        self.token = token
        self.timeout = timeout
        self.callback = callback
        self.event = None


class SessionManager(Thread, metaclass=Singleton):
    _event_loop = None
    _session_queue = Queue()
    _map = dict()
    _event_queue = Queue()

    def __init__(self):
        super().__init__()
        self.start()

    @staticmethod
    @asyncio.coroutine
    def _timer(session):
        try:
            yield from asyncio.wait_for(session.event.wait(), session.timeout)
            logger.debug('{} interrupted via timer'.format(session.token))
        except asyncio.TimeoutError:
            logger.debug('{} timed out'.format(session.token))
        del __class__._map[session.token]


    @staticmethod
    @asyncio.coroutine
    def _spawn():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                session = yield from __class__._event_loop.run_in_executor(
                    executor,
                    functools.partial(__class__._session_queue.get)
                )
                if not session.event:
                    session.event = asyncio.Event()
                    __class__._event_loop.create_task(__class__._timer(session))
                else:
                    logger.debug('{} interrupted'.format(session.token))


    @staticmethod
    @asyncio.coroutine
    def _interruptor():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                session = yield from __class__._event_loop.run_in_executor(
                    executor,
                    functools.partial(__class__._event_queue.get)
                )
                if type(session.event) is asyncio.Event:
                    session.event.set()


    @staticmethod
    def new(token, timeout, callback=None):
        session = Session(token, timeout, callback)
        __class__._map[token] = session
        __class__._session_queue.put(session)


    @staticmethod
    def interrupt(token):
        session = __class__._map[token]
        if not session.event:
            session.event = True
        __class__._event_queue.put(session)


    def run(self):
        try:
            __class__._event_loop = asyncio.get_event_loop()
        except AssertionError:
            logger.debug("no event loop found")
            __class__._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(__class__._event_loop)
            logger.debug("created new event loop")
        __class__._event_loop.create_task(__class__._interruptor())
        __class__._event_loop.create_task(__class__._spawn())
        __class__._event_loop.run_forever()
        __class__._event_loop.stop()
        __class__._event_loop.close()
