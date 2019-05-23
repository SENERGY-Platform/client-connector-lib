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

from collections import OrderedDict
from hashlib import sha1


class Device:
    """
    Subclass this class to create devices for use with the client-connector-lib.
    """
    def __new__(cls, *args, **kwargs):
        instance = super(Device, cls).__new__(cls)
        instance.__id = str()
        instance.__remote_id = str()
        instance.__type_id = str()
        instance.__name = str()
        instance.__tags = OrderedDict()
        return instance

    @property
    def id(self) -> str:
        return self.__id

    @id.setter
    def id(self, arg: str):
        if not type(arg) is str:
            raise TypeError(type(arg))
        if self.__id:
            raise AttributeError
        self.__id = arg

    @property
    def remote_id(self) -> str:
        return self.__remote_id

    @property
    def type_id(self) -> str:
        return self.__type_id

    @type_id.setter
    def type_id(self, arg):
        if not type(arg) is str:
            raise TypeError(type(arg))
        if self.__type_id:
            raise AttributeError
        self.__type_id = arg

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, arg: str) -> None:
        if not type(arg) is str:
            raise TypeError(type(arg))
        self.__name = arg

    @property
    def tags(self) -> list:
        """
        Combine tag IDs and tags as key:value pairs.
        :return: List.
        """
        return ['{}:{}'.format(key, value) for key, value in self.__tags.items()]

    @property
    def hash(self) -> str:
        """
        Uses device attributes to calculate a sha1 hash.
        :return: String.
        """
        return sha1(
            ''.join(
                (
                    self.id,
                    self.type_id,
                    self.name
                )
            ).encode()
        ).hexdigest()

    def addTag(self, tag_id: str, tag: str) -> None:
        """
        Add a tag to a device.
        :param: tag_id: ID identifying the tag.
        :param: tag: Word or combination of Words.
        :return: None.
        """
        if not type(tag_id) is str:
            raise TypeError(type(tag_id))
        if not type(tag) is str:
            raise TypeError(type(tag))
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
        try:
            del self.__tags[tag_id]
        except KeyError:
            raise KeyError("tag id '{}' does not exist".format(tag_id))

    def getService(self, service: str):
        if not type(service) is str:
            raise TypeError(type(service))
        return getattr(self, service)

    def __repr__(self, **kwargs):
        """
        Provide a string representation.
        :param kwargs: User attributes provided from subclass.
        :return: String.
        """
        attributes = [
            ('id', self.id),
            ('remote_id', self.remote_id),
            ('type_id', self.type_id),
            ('name', self.name),
            ('tags', self.tags),
            ('hash', self.hash),
            ('services', [item for item in dir(self) if getattr(getattr(self, item), "__service__", None)])
        ]
        if kwargs:
            for arg, value in kwargs.items():
                attributes.append((arg, value))
        return "{}({})".format(type(self).__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
