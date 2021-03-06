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


__all__ = ("CommandEnvelope", "EventEnvelope")


from ._message import Message
from ...types import Device
from ..._util import validateInstance
import typing
import uuid


class Envelope:

    __slots__ = ('__correlation_id', '__device_id', '__service_uri', '__message')

    def __init__(self, device: typing.Union[Device, str], service: str, message: Message, corr_id: typing.Optional[str] = None):
        if type(device) is str:
            self.__device_id = device
        elif type(device) is Device or issubclass(type(device), Device):
            self.__device_id = device.id
        else:
            raise TypeError(type(device))
        validateInstance(service, str)
        if corr_id:
            validateInstance(corr_id, str)
        self.__correlation_id = corr_id or str(uuid.uuid4())
        self.__service_uri = service
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
    def message(self) -> Message:
        return self.__message

    @message.setter
    def message(self, arg):
        validateInstance(arg, Message)
        self.__message = arg

    def __iter__(self):
        items = (
            ('correlation_id', self.correlation_id),
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
            ('message', self.message)
        ]
        return "{}({})".format(
            type(self).__name__,
            ", ".join(["=".join([key, str(value)]) for key, value in attributes])
        )


class CommandEnvelope(Envelope):

    __slots__ = ('__completion_strategy', '__timestamp')

    def __init__(
            self,
            device: typing.Union[Device, str],
            service: str, message: Message,
            corr_id: typing.Optional[str] = None,
            completion_strategy: typing.Optional[str] = None,
            timestamp: typing.Optional[float] = None
    ):
        super().__init__(device, service, message, corr_id)
        self.__completion_strategy = completion_strategy
        self.__timestamp = timestamp

    @property
    def completion_strategy(self) -> str:
        return self.__completion_strategy

    @property
    def timestamp(self) -> float:
        return self.__timestamp


class EventEnvelope(Envelope):

    def __init__(self, device: typing.Union[Device, str], service: str, message: Message):
        super().__init__(device, service, message)