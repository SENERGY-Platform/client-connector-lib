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

__all__ = ('Device', 'device')

from .._util import validateInstance, getSubclass
from ._service import Service
from collections import OrderedDict


class Device:
    uri = str()
    description = str()
    services = dict()

    def __new__(cls, *args, **kwargs):
        if cls is __class__:
            __err = "instantiation of class '{}' not allowed".format(__class__.__name__)
            raise TypeError(__err)
        __instance = super(__class__, cls).__new__(cls)
        __instance.__id = str()
        __instance.__remote_id = str()
        __instance.__name = str()
        __instance.__tags = OrderedDict()
        return __instance

    @property
    def id(self) -> str:
        return self.__id

    @id.setter
    def id(self, arg: str):
        validateInstance(arg, str)
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
        validateInstance(arg, str)
        self.__name = arg

    @property
    def tags(self) -> list:
        """
        Combine tag IDs and tags as key:value pairs.
        :return: List.
        """
        return ['{}:{}'.format(key, value) for key, value in self.__tags.items()]

    def addTag(self, tag_id: str, tag: str) -> None:
        """
        Add a tag to a device.
        :param: tag_id: ID identifying the tag.
        :param: tag: Word or combination of Words.
        :return: None.
        """
        validateInstance(tag_id, str)
        validateInstance(tag, str)
        if tag_id in self.__tags.keys():
            raise KeyError("tag id '{}' already in use".format(tag_id))
        if ':' in tag_id or ';' in tag_id:
            raise ValueError("tag id may not contain ':' or ';'")
        if ':' in tag or ';' in tag:
            raise ValueError("tag may not contain ':' or ';'")
        self.__tags[tag_id] = tag

    def changeTag(self, tag_id: str, tag: str) -> None:
        """
        Change existing tag.
        :param: tag_id: ID identifying the tag.
        :param: tag: Word or combination of Words.
        :return: None.
        """
        validateInstance(tag_id, str)
        validateInstance(tag, str)
        if ':' in tag or ';' in tag:
            raise ValueError("tag may not contain ':' or ';'")
        if tag_id in self.__tags:
            self.__tags[tag_id] = tag
        else:
            raise KeyError("tag id '{}' does not exist".format(tag_id))

    def removeTag(self, tag_id: str) -> None:
        """
        Remove existing tag.
        :param: tag_id: ID identifying the tag.
        :return: Boolean
        """
        validateInstance(tag_id, str)
        try:
            del self.__tags[tag_id]
        except KeyError:
            raise KeyError("tag id '{}' does not exist".format(tag_id))

    def getService(self, service: str) -> Service:
        try:
            return self.__class__.services[service]
        except KeyError:
            raise KeyError("service '{}' does not exist".format(service))

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
            ('tags', repr(self.tags)),
            ('services', [key for key in self.__class__.services])
        ]
        if kwargs:
            for arg, value in kwargs.items():
                attributes.append((arg, value))
        return "{}({})".format(type(self).__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))

    @classmethod
    def _validate(cls) -> None:
        for a_name, a_type in _getAttributes():
            attr = getattr(cls, a_name)
            validateInstance(attr, a_type)
            if a_name is "services":
                for key, srv in attr.items():
                    if isinstance(srv, type):
                        validateSubclass(srv, Service)
                    else:
                        validateInstance(srv, Service)
                    validateInstance(key, str)


def device(obj: Union[type, dict]) -> type:
    validateInstance(obj, (type, dict))
    return getSubclass(obj, Device)


def _getAttributes() -> tuple:
    return tuple((name, type(obj)) for name, obj in Device.__dict__.items() if
                 not name.startswith("_") and not isinstance(obj, staticmethod))