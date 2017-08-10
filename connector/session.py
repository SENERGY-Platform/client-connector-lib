if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, asyncio, concurrent.futures, time
from threading import Thread
from queue import Queue, Empty
from uuid import uuid4 as uuid


logger = root_logger.getChild(__name__)


class SessionManager(Thread, metaclass=Singleton):
    _event_loop = None
    _in = Queue()
    _map = dict()
    _inter = Queue()

    def __init__(self):
        super().__init__()
        self.start()

    @staticmethod
    @asyncio.coroutine
    def _timer(event, timeout, token):
        try:
            yield from asyncio.wait_for(event.wait(), timeout)
            logger.debug('{} interrupted'.format(token))
        except asyncio.TimeoutError:
            logger.debug('timed out')


    # noinspection PyTupleAssignmentBalance
    @staticmethod
    @asyncio.coroutine
    def _spawn():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                token, timeout = yield from __class__._event_loop.run_in_executor(
                    executor,
                    functools.partial(__class__._in.get)
                )
                event = asyncio.Event()
                __class__._map[token] = event
                __class__._event_loop.create_task(__class__._timer(event, timeout, token))


    @staticmethod
    @asyncio.coroutine
    def _interruptor():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                token = yield from __class__._event_loop.run_in_executor(
                    executor,
                    functools.partial(__class__._inter.get)
                )
                while not token in __class__._map:
                    yield
                __class__._map[token].set()


    @staticmethod
    def new(token, timeout):
        __class__._in.put((token, timeout))


    @staticmethod
    def interrupt(token):
        __class__._inter.put(token)


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
