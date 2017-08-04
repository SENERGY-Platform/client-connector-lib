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


class Communication(str):
    def __init__(self, token):
        super().__init__()
        self.callback = None
        self.handler = None
        self.message = None
        self.timeout = None
        self.retries = None
        self.retry_delay = None
        self.event = None


class CommManager(Thread, metaclass=Singleton):
    _async_spawn_input = Queue()
    _communications = list()
    _event_loop = None

    def __init__(self):
        super().__init__()
        self._stop_async = False

    @asyncio.coroutine
    def _commFuture(self, comm: Communication):
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
    def add(handler, callback, timeout=10, retries=0, retry_delay=0.5):  ###### remove defaults ######
        comm = Communication(uuid())
        comm.handler = handler
        comm.callback = callback
        comm.timeout = timeout
        comm.retries = retries
        comm.retry_delay = retry_delay
        comm.event = asyncio.Event(loop=__class__._event_loop)
        __class__._async_spawn_input.put(comm)
        __class__._communications.append(comm)

    @staticmethod
    def _remove(comm):
        __class__._communications.remove(comm)

    @staticmethod
    def _get(comm):
        pass





##### test #####
import random
fdsd = CommManager()
fdsd.start()

def doIt():
    time.sleep(random.uniform(0.0, 1.0))
    CommManager.add("asdfsdf", None, 10)

for x in range(15):
    doIt()


time.sleep(0.5)
CommManager._communications[6].event.set()
CommManager._communications[3].event.set()
time.sleep(3)
CommManager._communications[4].event.set()
CommManager._communications[13].event.set()
CommManager._communications[2].event.set()
##### test #####
