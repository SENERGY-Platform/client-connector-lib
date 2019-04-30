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
from typing import Type
from hashlib import sha1


class Device:
    """
    Use this class to create devices for use with the client-connector-lib.
    Subclass this class for advanced requirements. Don't forget to call __init__ of this class when subclassing.
    """
    def __init__(self, id: str, type: str, name: str):
        """
        Create a device object. Checks if parameters meet type requirements.
        :param id: Local device ID.
        :param type: Device type (create device types via platform gui).
        :param name: Device name.
        :param services: List or tuple of Service objects.
        :return: Device object.
        """
        __class__.__checkType(id, str)
        __class__.__checkType(type, str)
        __class__.__checkType(name, str)
        self.__id = id
        self.__remote_id = None
        self.__type = type
        self.__name = name
        self.__tags = OrderedDict()
        # self.__img_url = None

    @property
    def id(self) -> str:
        return self.__id

    @property
    def remote_id(self) -> str:
        return self.__remote_id

    @property
    def type(self) -> str:
        return self.__type

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, arg: str) -> None:
        if type(arg) is not str:
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
                    self.__id,
                    self.__type,
                    self.__name,
                    ''.join(['{}{}'.format(key, value) for key, value in self.__tags.items()])
                )
            ).encode()
        ).hexdigest()

    # @property
    # def img_url(self) -> str:
    #     return self.__img_url
    #
    # @img_url.setter
    # def img_url(self, arg):
    #     if type(arg) is not str:
    #         raise TypeError("image url must be a string but got '{}'".format(type(arg)))
    #     self.__img_url = arg

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

    @staticmethod
    def __checkType(arg: object, typ: Type) -> None:
        """
        Check if arg is the correct type. Raise exception if not.
        :param: arg: object to check
        :param: typ: type
        """
        if not type(arg) is typ:
            raise TypeError(type(arg))

    def __repr__(self, **kwargs):
        """
        Provide a string representation.
        :param kwargs: User attributes provided from subclass.
        :return: String.
        """
        attributes = [
            ('id', self.id),
            ('type', self.type),
            ('name', self.name),
            ('tags', self.tags),
            ('hash', self.hash),
            # ('img_url', self.img_url),
            ('remote_id', self.remote_id)
        ]
        if kwargs:
            for arg, value in kwargs.items():
                attributes.append((arg, value))
        return "{}({})".format(type(self).__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))

