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

__all__ = ('Device', 'device', 'ServiceNotFoundError')

from .._util import validate_instance, getSubclass
from ._service import Service


class ServiceNotFoundError(Exception):
    pass


class Device:
    device_type_id = str()
    services = tuple()
    _service_map = dict()

    def __new__(cls, *args, **kwargs):
        if cls is __class__:
            __err = "instantiation of class '{}' not allowed".format(__class__.__name__)
            raise TypeError(__err)
        if not cls._service_map:
            cls._service_map = {srv.local_id: srv for srv in cls.services}
        __instance = super(__class__, cls).__new__(cls)
        __instance.__id = str()
        __instance.__remote_id = str()
        __instance.__name = str()
        return __instance

    @property
    def id(self) -> str:
        return self.__id

    @id.setter
    def id(self, arg: str):
        validate_instance(arg, str)
        if self.__id:
            raise AttributeError
        self.__id = arg

    @property
    def remote_id(self) -> str:
        return self.__remote_id

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, arg: str) -> None:
        validate_instance(arg, str)
        self.__name = arg

    def getService(self, service: str) -> Service:
        try:
            return self.__class__._service_map[service]
        except KeyError:
            raise ServiceNotFoundError("'{}' does not exist for '{}'".format(service, self.__class__.__name__))

    def __str__(self, **kwargs):
        """
        Provide a string representation.
        :param kwargs: User attributes provided from subclass.
        :return: String.
        """
        attributes = [
            ('id', repr(self.id)),
            ('remote_id', repr(self.remote_id)),
            ('name', repr(self.name)),
            ('services', [key for key in self.__class__.services])
        ]
        if kwargs:
            for arg, value in kwargs.items():
                attributes.append((arg, value))
        return "{}({})".format(self.__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))


def device(obj: type) -> type:
    validate_instance(obj, type)
    return getSubclass(obj, Device)
