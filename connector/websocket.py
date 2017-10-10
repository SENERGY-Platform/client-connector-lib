if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    import websockets
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import asyncio
import concurrent.futures
import functools
from queue import Queue, Empty
from threading import Thread, Event
from time import sleep

logger = root_logger.getChild(__name__)


class Websocket(Thread):
    def __init__(self, host, port, exit_callbck=None):
        super().__init__()
        self._host = host
        self._port = port
        self._function_queue = Queue(1)
        self._stop_async = False
        self._websocket = None
        self._exit_callbck = exit_callbck


    def _functionQueuePut(self, function, *args, **kwargs):
        self._function_queue.put((function, args, kwargs))


    def _retrieveAsyncResult(self, task):
        if task.exception():
            task.cancel()
        else:
            task.result()
        logger.debug("{}".format(task))


    @asyncio.coroutine
    def _spawnAsync(self):
        tasks = list()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while not self._stop_async:
                try:
                    function, args, kwargs = yield from self._event_loop.run_in_executor(
                        executor,
                        functools.partial(self._function_queue.get, timeout=1)
                    )
                    tasks.append(self._event_loop.create_task(function(*args, **kwargs)))
                except Empty:
                    pass
            asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
        logger.debug("_spawnAsync() exited")


    def run(self):
        try:
            self._event_loop = asyncio.get_event_loop()
        except AssertionError:
            logger.debug("no event loop found")
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            logger.debug("created new event loop")
        self._event_loop.run_until_complete(self._spawnAsync())
        self._event_loop.stop()
        self._event_loop.close()
        if self._exit_callbck:
            self._exit_callbck()


    @asyncio.coroutine
    def _connect(self, callback):
        asyncio.Task.current_task().add_done_callback(self._retrieveAsyncResult)
        try:
            self._websocket = yield from websockets.connect(
                'ws://{}:{}'.format(self._host, self._port),
                loop=self._event_loop
            )
            logger.debug("connected to '{}' on '{}'".format(self._host, self._port))
            callback(True)
        except (OSError, websockets.InvalidHandshake, websockets.InvalidURI) as ex:
            logger.debug("could not connect to '{}' on '{}'".format(self._host, self._port))
            logger.debug(ex)
            callback(False)

    def connect(self, callback):
        self._functionQueuePut(self._connect, callback)
        self.start()


    @asyncio.coroutine
    def _shutdown(self, callback=None):
        asyncio.Task.current_task().add_done_callback(self._retrieveAsyncResult)
        logger.debug("stopping async tasks")
        self._stop_async = True
        if self._websocket:
            logger.debug("closing connection")
            yield from self._websocket.close(code=1000, reason='closed by client')
        if callback:
            callback()

    def shutdown(self, callback):
        self._functionQueuePut(self._shutdown, callback)


    @asyncio.coroutine
    def _send(self, callback, payload):
        asyncio.Task.current_task().add_done_callback(self._retrieveAsyncResult)
        try:
            yield from self._websocket.send(payload)
            callback(True)
        except (websockets.WebSocketProtocolError, websockets.ConnectionClosed, BrokenPipeError, TypeError) as ex:
            logger.warning("could not send data")
            logger.error(ex)
            callback(False)

    def send(self, callback, payload):
        self._functionQueuePut(self._send, callback, payload)


    @asyncio.coroutine
    def _receive(self, callback):
        asyncio.Task.current_task().add_done_callback(self._retrieveAsyncResult)
        try:
            payload = yield from self._websocket.recv()
            callback(payload)
        except (websockets.ConnectionClosed, websockets.WebSocketProtocolError) as ex:
            logger.error(ex)
            callback(False)

    def receive(self, callback):
        self._functionQueuePut(self._receive, callback)


    @asyncio.coroutine
    def _ioRecv(self, callback, in_queue):
        asyncio.Task.current_task().add_done_callback(self._retrieveAsyncResult)
        logger.debug("io receive task started")
        callback()
        while not self._stop_async:
            try:
                payload = yield from self._websocket.recv()
                in_queue.put(payload)
            except (websockets.ConnectionClosed, websockets.WebSocketProtocolError) as ex:
                logger.error(ex)
                break
        if not self._stop_async:
            yield from self._shutdown()


    @asyncio.coroutine
    def _ioSend(self, callback, out_queue):
        asyncio.Task.current_task().add_done_callback(self._retrieveAsyncResult)
        logger.debug("io send task started")
        callback()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while not self._stop_async:
                try:
                    payload = yield from self._event_loop.run_in_executor(
                        executor,
                        functools.partial(out_queue.get, timeout=1)
                    )
                    try:
                        yield from self._websocket.send(payload)
                    except (websockets.WebSocketProtocolError, websockets.ConnectionClosed, BrokenPipeError, TypeError) as ex:
                        logger.warning("could not send data")
                        logger.error(ex)
                        break
                except Empty:
                    pass
        if not self._stop_async:
            yield from self._shutdown()


    def ioStart(self, callback, in_queue, out_queue):
        event = Event()
        self._functionQueuePut(self._ioRecv, event.set, in_queue)
        event.wait()
        event.clear()
        self._functionQueuePut(self._ioSend, event.set, out_queue)
        event.wait()
        callback()
