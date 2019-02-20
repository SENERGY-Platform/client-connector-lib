"""
   Copyright 2019 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

try:
    import websockets
    from ...logger import root_logger, connector_lib_log_handler
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import asyncio, concurrent.futures, functools, logging, time
from queue import Queue, Empty
from threading import Thread, Event

logger = root_logger.getChild(__name__.split('.', 1)[-1])
ws_logger = logging.getLogger('websockets')
ws_logger.setLevel(logging.INFO)
ws_logger.addHandler(connector_lib_log_handler)


class Websocket(Thread):
    def __init__(self, protocol, host, port, exit_callbck=None):
        super().__init__()
        self.setName('Websocket')
        self._host = host
        self._port = port
        self._protocol = protocol
        self._function_queue = Queue(1)
        self._stop_async = False
        self._websocket = None
        self._exit_callbck = exit_callbck


    def _functionQueuePut(self, function, *args, **kwargs):
        self._function_queue.put((function, args, kwargs))


    async def _spawnAsync(self):
        tasks = list()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='Websocket_spawnAsync') as executor:
            while not self._stop_async:
                try:
                    function, args, kwargs = await self._event_loop.run_in_executor(
                        executor,
                        functools.partial(self._function_queue.get, timeout=1)
                    )
                    tasks.append(self._event_loop.create_task(function(*args, **kwargs)))
                except Empty:
                    pass
            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED, timeout=30, loop=self._event_loop)
            logger.debug("done tasks: {}".format(done))
            if pending:
                logger.error("could not finish tasks: {}".format(pending))
        logger.debug("_spawnAsync() exited")


    def run(self):
        try:
            self._event_loop = asyncio.get_event_loop()
        except (RuntimeError, AssertionError):
            logger.debug("no event loop found")
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            logger.debug("created new event loop")
        self._event_loop.run_until_complete(self._spawnAsync())
        self._event_loop.stop()
        self._event_loop.close()
        if self._exit_callbck:
            self._exit_callbck()


    async def _connect(self, callback):
        try:
            if float(websockets.__version__) > 6.0:
                self._websocket = await websockets.connect(
                    '{}://{}:{}'.format(self._protocol, self._host, self._port),
                    ping_interval=None,
                    ping_timeout=None,
                    loop=self._event_loop
                )
            else:
                self._websocket = await websockets.connect(
                    '{}://{}:{}'.format(self._protocol, self._host, self._port),
                    loop=self._event_loop
                )
            logger.debug("connected to '{}' on '{}'".format(self._host, self._port))
            callback(True)
        except Exception as ex:
            logger.debug("could not connect to '{}' on '{}'".format(self._host, self._port))
            logger.debug(ex)
            callback(False)

    def connect(self, callback):
        self._functionQueuePut(self._connect, callback)
        self.start()


    async def _shutdown(self, callback=None, lost_con=None):
        logger.debug("stopping async tasks")
        self._stop_async = True
        if self._websocket and self._websocket.open:
            if lost_con:
                logger.info("failing connection")
                self._websocket.connection_lost(None)
                await self._websocket.wait_for_connection_lost()
            else:
                logger.info("closing connection")
                try:
                    await self._websocket.close(code=1000, reason='closed by client')
                except Exception as ex:
                    logger.error(ex)
        if callback:
            callback()

    def shutdown(self, callback):
        self._functionQueuePut(self._shutdown, callback)


    async def _send(self, callback, payload):
        try:
            await self._websocket.send(payload)
            callback(True)
        except Exception as ex:
            logger.warning("could not send data - {}".format(ex))
            callback(False)

    def send(self, callback, payload):
        self._functionQueuePut(self._send, callback, payload)


    async def _receive(self, callback):
        try:
            payload = await asyncio.wait_for(self._websocket.recv(), timeout=20, loop=self._event_loop)
            callback(payload)
        except Exception as ex:
            if not self._stop_async:
                logger.warning("could not receive data - {}".format(ex))
            callback(False)

    def receive(self, callback):
        self._functionQueuePut(self._receive, callback)


    async def _ioRecv(self, callback, in_queue):
        logger.debug("io receive task started")
        callback()
        while not self._stop_async:
            try:
                payload = await asyncio.wait_for(self._websocket.recv(), timeout=15, loop=self._event_loop)
                in_queue.put(payload)
            except (TimeoutError, asyncio.TimeoutError):
                pong = await self._websocket.ping(str(int(time.time())))
                logger.debug("sent ping after 15s of inactivity")
                done, pending = await asyncio.wait([pong], timeout=10, loop=self._event_loop)
                if pending:
                    logger.error("pong timeout")
                    if not self._stop_async:
                        self._functionQueuePut(self._shutdown, lost_con=True)
                    try:
                        await pong
                    except Exception:
                        logger.debug("retrieved exception from pong future")
                    return
                if done and not pong.cancelled():
                    logger.debug("received pong")
            except Exception as ex:
                if not self._stop_async:
                    logger.warning("could not receive data - {}".format(ex))
                break
        if not self._stop_async:
            self._functionQueuePut(self._shutdown)


    async def _ioSend(self, callback, out_queue):
        logger.debug("io send task started")
        callback()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='Websocket_ioSend') as executor:
            while not self._stop_async:
                try:
                    payload = await self._event_loop.run_in_executor(
                        executor,
                        functools.partial(out_queue.get, timeout=1)
                    )
                    try:
                        if not self._stop_async:
                            await self._websocket.send(payload)
                    except Exception as ex:
                        logger.warning("could not send data - {}".format(ex))
                        break
                except Empty:
                    pass
        if not self._stop_async:
            self._functionQueuePut(self._shutdown)


    def ioStart(self, callback, in_queue, out_queue):
        event = Event()
        self._functionQueuePut(self._ioRecv, event.set, in_queue)
        event.wait()
        event.clear()
        self._functionQueuePut(self._ioSend, event.set, out_queue)
        event.wait()
        callback()
