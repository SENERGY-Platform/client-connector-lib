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

__all__ = ('Device', )

from .._util import validate_instance
import typing


def gen_attribute(key, value):
    validate_instance(key, str)
    validate_instance(value, (str, int, float))
    return {DeviceAttribute.key: key, DeviceAttribute.value: value}


class DeviceAttribute:
    key = "key"
    value = "value"
    origin = "origin"


class Device:
    def __init__(self, id: str, name: str, device_type_id: str, attributes: typing.Optional[typing.List[typing.Dict[str, typing.Union[str, int, float]]]] = None):
        validate_instance(id, str)
        validate_instance(device_type_id, str)
        self.__id = id
        self.__device_type_id = device_type_id
        self.__remote_id = None
        self.__attributes = None
        self.attributes = attributes or list()
        self.name = name

    @property
    def id(self) -> str:
        return self.__id

    @property
    def remote_id(self) -> str:
        return self.__remote_id

    @property
    def device_type_id(self) -> str:
        return self.__device_type_id

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, arg: str):
        validate_instance(arg, str)
        self.__name = arg

    @property
    def attributes(self) -> typing.List[typing.Dict[str, typing.Union[str, int, float]]]:
        return [obj.copy() for obj in self.__attributes]

    @attributes.setter
    def attributes(self, arg: typing.List[typing.Dict[str, typing.Union[str, int, float]]]):
        validate_instance(arg, (list, tuple))
        attributes = list()
        for item in arg:
            attributes.append(gen_attribute(**item))
        self.__attributes = attributes

    def __str__(self, **kwargs):
        """
        Provide a string representation.
        :param kwargs: User properties provided from subclass.
        :return: String.
        """
        properties = [
            ('id', repr(self.id)),
            ('remote_id', repr(self.remote_id)),
            ('name', repr(self.name)),
            ('device_type_id', repr(self.device_type_id)),
            ('attributes', repr(self.__attributes))
        ]
        if kwargs:
            for arg, value in kwargs.items():
                properties.append((arg, value))
        return "{}({})".format(self.__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in properties]))
