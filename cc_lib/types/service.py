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

__all__ = ('Service', )

from ..util import Singleton
from typing import Callable, Any


class Service(metaclass=Singleton):
    def __new__(cls, *args, **kwargs):
        instance = super(Service, cls).__new__(cls)
        instance.__input = None
        instance.__output = None
        instance.__uri = str()
        instance.__type = str()
        instance.__name = str()
        instance.__description = str()
        return instance

    @property
    def input(self) -> dict:
        return self.__input

    @input.setter
    def input(self, arg):
        if not type(arg) is dict:
            raise TypeError(type(arg))
        if self.__input:
            raise AttributeError
        self.__input = arg

    @property
    def output(self) -> dict:
        return self.__output

    @output.setter
    def output(self, arg):
        if not type(arg) is dict:
            raise TypeError(type(arg))
        if self.__output:
            raise AttributeError
        self.__output = arg

    @property
    def uri(self) -> str:
        return self.__uri

    @uri.setter
    def uri(self, arg: str):
        if not type(arg) is str:
            raise TypeError(type(arg))
        if self.__uri:
            raise AttributeError
        self.__uri = arg

    @property
    def type(self) -> str:
        return self.__type

    @type.setter
    def type(self, arg: str):
        if not type(arg) is str:
            raise TypeError(type(arg))
        if self.__type:
            raise AttributeError
        self.__type = arg

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, arg: str) -> None:
        if not type(arg) is str:
            raise TypeError(type(arg))
        self.__name = arg

    @property
    def description(self) -> str:
        return self.__description

    @description.setter
    def description(self, arg: str) -> None:
        if not type(arg) is str:
            raise TypeError(type(arg))
        self.__description = arg

    def task(self, func: Callable[[Any], Any]):
        def wrap(*args, **kwargs):
            return func(*args, **kwargs)
        setattr(wrap, "__service_task__", self)
        return wrap
