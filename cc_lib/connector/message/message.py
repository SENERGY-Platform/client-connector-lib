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


__all__ = ("Message", "Envelope")


from typing import Union
from uuid import uuid4 as uuid


class Message:
    def __init__(self, data: str, metadata: str):
        self.metadata = metadata
        self.data = data

    @property
    def metadata(self) -> str:
        return self.__metadata

    @metadata.setter
    def metadata(self, arg: str):
        if not type(arg) is str:
            raise TypeError(type(arg))
        self.__metadata = arg

    @property
    def data(self) -> str:
        return self.__data

    @data.setter
    def data(self, arg: str):
        if not type(arg) is str:
            raise TypeError(type(arg))
        self.__data = arg

    def __repr__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('metadata', self.metadata),
            ('data', self.data)
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))


class Envelope:
    def __init__(self, device_id: str, service_uri: str, message: Message, corr_id: Union[str, None] = None):
        if corr_id and not type(corr_id) is str:
            raise TypeError(type(corr_id))
        self.__correlation_id = corr_id or uuid().hex
        self.device_id = device_id
        self.service_uri = service_uri
        self.message = message

    @property
    def correlation_id(self) -> str:
        return self.__correlation_id

    @property
    def device_id(self) -> str:
        return self.__device_id

    @device_id.setter
    def device_id(self, arg: str):
        if not type(arg) is str:
            raise TypeError(type(arg))
        self.__device_id = arg

    @property
    def service_uri(self) -> str:
        return self.__service_uri

    @service_uri.setter
    def service_uri(self, arg):
        if not type(arg) is str:
            raise TypeError(type(arg))
        self.__service_uri = arg

    @property
    def message(self) -> Message:
        return self.__message

    @message.setter
    def message(self, arg):
        if not type(arg) is Message:
            raise TypeError(type(arg))
        self.__message = arg

    def __repr__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('correlation_id', self.correlation_id),
            ('device_id', self.device_id),
            ('service_uri', self.service_uri),
            ('message', self.message)
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
