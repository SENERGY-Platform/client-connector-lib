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
        self.envelope = None
        self.event = None


class TokenManager(Thread, metaclass=Singleton):
    _async_spawn_input = Queue()
    _tokens = list()
    _event_loop = None

    def __init__(self):
        super().__init__()
        self._stop_async = False

    @asyncio.coroutine
    def _commFuture(self, comm):
        try:
            yield from asyncio.wait_for(comm.event.wait(), comm.timeout)
            logger.debug(comm + ' got response')
        except asyncio.TimeoutError:
            logger.debug(comm + ' timed out')

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
    def add():
        comm = Token(uuid())
        comm.event = asyncio.Event(loop=__class__._event_loop)
        __class__._async_spawn_input.put(comm)
        __class__._tokens.append(comm)

    @staticmethod
    def _remove(comm):
        __class__._tokens.remove(comm)

    @staticmethod
    def _get(comm):
        pass
