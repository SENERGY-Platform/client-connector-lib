if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
    from connector.message.connector import Error
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, asyncio, concurrent.futures
from threading import Thread
from queue import Queue

logger = root_logger.getChild(__name__)


class Session:
    def __init__(self, message, timeout, retries, callback):
        self.message = message
        self.timeout = timeout
        self.callback = callback
        self.retries = retries
        self.event = None


class SessionManager(Thread, metaclass=Singleton):
    _event_loop = None
    _session_queue = Queue()
    _sessions = dict()
    _event_queue = Queue()
    callback_queue = Queue()

    def __init__(self):
        super().__init__()


    @staticmethod
    def _cleanup(session):
        if session.callback:
            __class__.callback_queue.put((session.callback, session.message))
        del __class__._sessions[session.message._token]


    @staticmethod
    @asyncio.coroutine
    def _timer(session):
        try:
            yield from asyncio.wait_for(session.event.wait(), session.timeout)
            logger.debug('{} caught event via _timer'.format(session.message._token))
        except asyncio.TimeoutError:
            logger.debug('{} timed out'.format(session.message._token))
            err_msg = Error('timeout')
            err_msg._token = session.message._token
            session.message = err_msg
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
                    logger.debug('{} caught event'.format(session.message._token))
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
    def new(message, timeout, retries, callback):
        session = Session(message, timeout, retries, callback)
        __class__._sessions[message._token] = session
        __class__._session_queue.put(session)


    @staticmethod
    def raiseEvent(msg_obj):
        session = __class__._sessions.get(msg_obj._token)
        if session:
            session.message = msg_obj
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
