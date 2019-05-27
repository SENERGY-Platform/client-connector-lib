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

__all__ = ('Service', 'actuator', 'sensor')

from ..._util import Singleton


actuator = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Actuator"
sensor = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Sensor"


class Service(metaclass=Singleton):
    def __new__(cls, *args, **kwargs):
        if cls is __class__:
            __err = "direct instantiation of class '{}' not allowed".format(__class__.__name__)
            raise TypeError(__err)
        __instance = super(Service, cls).__new__(cls)
        __instance.__input = None
        __instance.__output = None
        __instance.__uri = str()
        __instance.__type = str()
        __instance.__name = str()
        __instance.__description = str()
        if not hasattr(__instance, "task") or not callable(getattr(__instance, "task")):
            __err = "can't instantiate class '{}' with required method 'task'".format(cls.__name__)
            raise TypeError(__err)
        return __instance

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


# class Actuator(_Service):
#     def __new__(cls, *args, **kwargs):
#         __instance = super().__new__(cls, *args, **kwargs)
#         setattr(
#             __instance,
#             "{}__type".format(_Service.__name__),
#             "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Actuator"
#         )
#         return __instance
#
#
# class Sensor(_Service):
#     def __new__(cls, *args, **kwargs):
#         __instance = super().__new__(cls, *args, **kwargs)
#         setattr(
#             __instance,
#             "{}__type".format(_Service.__name__),
#             "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Sensor"
#         )
#         return __instance
