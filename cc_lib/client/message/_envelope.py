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


__all__ = ("Envelope", )


from ._message import Message
from ...types import Device
from typing import Optional, Type, Union
from uuid import uuid4 as uuid


class Envelope:

    __slots__ = ('__correlation_id', '__device_id', '__service_uri', '__message', '__cmd_strategy', '__cmd_timestamp')

    def __init__(
            self,
            device: Union[Device, str],
            service: str, message: Message,
            corr_id: Optional[str] = None,
            cmd_strategy: Optional[str] = None,
            cmd_timestamp: Optional[float] = None
    ):
        if type(device) is str:
            self.__device_id = device
        elif type(device) is Device or issubclass(type(device), Device):
            self.__device_id = device.id
        else:
            raise TypeError(type(device))
        __class__.__checkType(service, str)
        if corr_id:
            __class__.__checkType(corr_id, str)
        self.__correlation_id = corr_id or str(uuid())
        self.__service_uri = service
        self.__cmd_strategy = cmd_strategy
        self.__cmd_timestamp = cmd_timestamp
        self.message = message

    @property
    def correlation_id(self) -> str:
        return self.__correlation_id

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def service_uri(self) -> str:
        return self.__service_uri

    @property
    def cmd_strategy(self) -> str:
        return self.__cmd_strategy

    @property
    def cmd_timestamp(self) -> float:
        return self.__cmd_timestamp

    @property
    def message(self) -> Message:
        return self.__message

    @message.setter
    def message(self, arg):
        __class__.__checkType(arg, Message)
        self.__message = arg

    @staticmethod
    def __checkType(arg: object, typ: Type) -> None:
        """
        Check if arg is the correct type. Raise exception if not.
        :param: arg: object to check
        :param: typ: type
        """
        if not type(arg) is typ:
            raise TypeError(type(arg))

    def __iter__(self):
        items = (
            ('correlation_id', self.correlation_id),
            ('completion_strategy', self.cmd_strategy),
            ('payload', dict(self.message))
        )
        for item in items:
            yield item

    def __str__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('correlation_id', self.correlation_id),
            ('device_id', self.device_id),
            ('service_uri', self.service_uri),
            ('cmd_strategy', self.cmd_strategy),
            ('cmd_timestamp', self.cmd_timestamp),
            ('message', self.message)
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
