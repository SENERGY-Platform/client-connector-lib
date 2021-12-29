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

from typing import Optional, List, Dict

from .._util import validate_instance


class Device:
    def __init__(self, id: str, name: str, device_type_id: str, attributes: Optional[List[Dict]] = None):
        validate_instance(id, str)
        validate_instance(device_type_id, str)
        self.__id = id
        self.__device_type_id = device_type_id
        self.__remote_id = None
        self.__attributes = attributes
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

    @property
    def attributes(self) -> Optional[List[Dict]]:
        return self.__attributes

    @name.setter
    def name(self, arg: str) -> None:
        validate_instance(arg, str)
        self.__name = arg

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
            ('attributes', repr(self.attributes))
        ]
        if kwargs:
            for arg, value in kwargs.items():
                properties.append((arg, value))
        return "{}({})".format(self.__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in properties]))
