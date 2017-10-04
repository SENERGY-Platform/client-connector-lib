if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from connector.message import Message
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, asyncio, concurrent.futures
from threading import Thread
from queue import Queue

logger = root_logger.getChild(__name__)


class Session:
    def __init__(self, msg_obj, token, timeout, callback):
        self.msg_obj = msg_obj
        self.token = token
        self.timeout = timeout
        self.callback = callback
        self.event = None


class SessionManager(Thread, metaclass=Singleton):
    _event_loop = None
    _session_queue = Queue()
    _sessions = dict()
    _event_queue = Queue()
    callback_queue = Queue()

    def __init__(self):
        super().__init__()
        self.start()


    @staticmethod
    def _cleanup(session):
        if session.callback:
            __class__.callback_queue.put((session.callback, session.msg_obj))
        del __class__._sessions[session.token]


    @staticmethod
    @asyncio.coroutine
    def _timer(session):
        try:
            yield from asyncio.wait_for(session.event.wait(), session.timeout)
            logger.debug('{} caught event (timer)'.format(session.token))
        except asyncio.TimeoutError:
            logger.warning('{} timed out'.format(session.token))
            session.msg_obj.payload = 'timed out'
        __class__._cleanup(session)


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
                    logger.debug('{} caught event'.format(session.token))
                    __class__._cleanup(session)


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
    def new(msg_obj, token, timeout, callback):
        session = Session(msg_obj, token, timeout, callback)
        __class__._sessions[token] = session
        __class__._session_queue.put(session)


    @staticmethod
    def raiseEvent(msg_obj, token):
        session = __class__._sessions.get(token)
        if session:
            session.msg_obj = msg_obj
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
