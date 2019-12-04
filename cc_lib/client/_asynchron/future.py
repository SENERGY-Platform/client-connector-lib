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

__all__ = ('Future', )


from .._exception import FutureNotDoneError
import typing


class Future:

    __slots__ = ('__worker', )

    def __init__(self, worker):
        self.__worker = worker

    def result(self) -> typing.Any:
        if not self.__worker.done:
            raise FutureNotDoneError
        if self.__worker.exception:
            raise self.__worker.exception
        return self.__worker.result

    def done(self) -> bool:
        return self.__worker.done

    def running(self) -> bool:
        return not self.__worker.done

    def wait(self, timeout: typing.Optional[float] = None) -> None:
        self.__worker.join(timeout)

    # def addDoneCallback(self, func: typing.Callable[[], None]) -> None:
    #     self.__worker.callback = func

    @property
    def name(self) -> str:
        return self.__worker.name
