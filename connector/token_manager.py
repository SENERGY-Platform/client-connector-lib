if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from modules.singleton import Singleton
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import functools, time, asyncio, concurrent.futures
from uuid import uuid4 as uuid
from threading import Thread
from queue import Queue, Empty

logger = root_logger.getChild(__name__)


class Token(str):
    def __init__(self, token):
        super().__init__()
        self.callback = None
        self.package = None
        self.event = None
        self.timeout = None


class TokenManager(Thread, metaclass=Singleton):
    _async_spawn_input = Queue()
    _tokens = set()
    _event_loop = None

    def __init__(self):
        super().__init__()
        self._stop_async = False

    @asyncio.coroutine
    def _commFuture(self, token):
        try:
            yield from asyncio.wait_for(token.event.wait(), token.timeout)
            logger.debug(token + ' got response')
        except asyncio.TimeoutError:
            logger.debug(token + ' timed out')

    @asyncio.coroutine
    def _spawnFuture(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while not self._stop_async:
                try:
                    communication = yield from __class__._event_loop.run_in_executor(
                        executor,
                        functools.partial(self._async_spawn_input.get, timeout=1)
                    )
                    logger.debug(">> " + communication)
                    __class__._event_loop.create_task(self._commFuture(communication))
                except Empty:
                    pass
        logger.debug("spawnFuture exited")

    def run(self):
        try:
            __class__._event_loop = asyncio.get_event_loop()
        except AssertionError:
            logger.debug("no event loop found")
            __class__._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(__class__._event_loop)
            logger.debug("created new event loop")
        __class__._event_loop.run_until_complete(self._spawnFuture())
        __class__._event_loop.stop()
        __class__._event_loop.close()

    @staticmethod
    def add(token, package, callback=None, timeout=None):
        token_obj = Token(token)
        token_obj.package = package
        token_obj.callback = callback
        token_obj.timeout = timeout
        token_obj.event = asyncio.Event(loop=__class__._event_loop)
        __class__._async_spawn_input.put(token_obj)
        __class__._tokens.add(token_obj)

    @staticmethod
    def _remove(token):
        __class__._tokens.remove(token)

    @staticmethod
    def _get(comm):
        pass
