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


__all__ = ('ThreadWorker', 'EventWorker')


from .future import Future
import threading
import typing


class ThreadWorker(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
        super().__init__(group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)
        self.result = None
        self.exception = None
        self.done = False
        # self.callback = None

    def run(self) -> None:
        try:
            try:
                if self._target:
                    self.result = self._target(*self._args, **self._kwargs)
            finally:
                del self._target, self._args, self._kwargs
        except Exception as ex:
            self.exception = ex
        self.done = True
        # if self.callback:
        #     try:
        #         self.callback()
        #     except BaseException:
        #         logger.exception("exception calling callback for '{}'".format(self.name))

    def start(self) -> Future:
        future = Future(self)
        super().start()
        return future

    def join(self, timeout: typing.Optional[float] = None) -> None:
        super().join(timeout)
        if self.is_alive():
            raise TimeoutError


class EventWorker(threading.Event):

    __slots__ = (
        'name', 'result', 'exception', 'usr_method', '_flag', '_cond', '__target', '__args', '__kwargs', '__started'
    )

    def __init__(self, target=None, name=None, args=(), kwargs=None, *, usr_method=None, usr_data=None):
        super().__init__()
        self.name = name
        self.result = None
        self.exception = None
        self.usr_method = usr_method
        self.usr_data = usr_data
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs
        self.__started = False

    @property
    def done(self):
        return self.is_set()

    def run(self) -> None:
        try:
            try:
                if self.__target:
                    if not self.__kwargs:
                        self.__kwargs = dict()
                    self.__kwargs["event_worker"] = self
                    self.__target(*self.__args, **self.__kwargs)
            finally:
                del self.__target, self.__args, self.__kwargs
        except Exception as ex:
            self.exception = ex
            self.set()

    def join(self, timeout: typing.Optional[float] = None) -> None:
        if not self.wait(timeout):
            raise TimeoutError

    def start(self) -> Future:
        if self.__started is True:
            raise RuntimeError
        future = Future(self)
        self.__started = True
        self.run()
        return future
