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


__all__ = ("CommandEnvelope", "CommandResponseEnvelope", "EventEnvelope", "FogProcessesEnvelope", "response_from_command_envelope")


from ._message import *
from ...types import Device
from ..._util import validate_instance
import typing
import uuid


class Envelope:

    __slots__ = ('__message', '__correlation_id')

    def __init__(self, message: typing.Any = None, corr_id: typing.Optional[str] = None):
        if corr_id:
            validate_instance(corr_id, str)
        self.__correlation_id = corr_id or str(uuid.uuid4())
        self.message = message

    @property
    def correlation_id(self) -> str:
        return self.__correlation_id

    @property
    def message(self) -> typing.Any:
        return self.__message

    @message.setter
    def message(self, arg):
        self.__message = arg

    def __str__(self, **kwargs):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('correlation_id', repr(self.correlation_id)),
            ('message', repr(self.message))
        ]
        if kwargs:
            for arg, value in kwargs.items():
                attributes.append((arg, repr(value)))
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(["=".join([key, str(value)]) for key, value in attributes])
        )


class DeviceEnvelope(Envelope):

    __slots__ = ('__device_id', '__service_uri')

    def __init__(
            self,
            device: typing.Union[Device, str],
            service: str,
            message: DeviceMessage,
            corr_id: typing.Optional[str] = None
    ):
        super().__init__(message=message, corr_id=corr_id)
        if type(device) is str:
            self.__device_id = device
        elif type(device) is Device or issubclass(type(device), Device):
            self.__device_id = device.id
        else:
            raise TypeError(type(device))
        validate_instance(service, str)
        self.__service_uri = service

    @property
    def device_id(self) -> str:
        return self.__device_id

    @property
    def service_uri(self) -> str:
        return self.__service_uri

    @property
    def message(self) -> DeviceMessage:
        return Envelope.message.fget(self)

    @message.setter
    def message(self, arg):
        validate_instance(arg, DeviceMessage)
        Envelope.message.fset(self, arg)

    def __iter__(self):
        items = (
            ('correlation_id', self.correlation_id),
            ('payload', dict(self.message))
        )
        for item in items:
            yield item

    def __str__(self, **kwargs):
        return super().__str__(device_id=self.device_id, service_uri=self.service_uri, **kwargs)


class CommandEnvelope(DeviceEnvelope):

    __slots__ = ('__completion_strategy', '__timestamp')

    def __init__(
            self,
            device: typing.Union[Device, str],
            service: str,
            message: DeviceMessage,
            corr_id: str,
            completion_strategy: str,
            timestamp: float
    ):
        super().__init__(device=device, service=service, message=message, corr_id=corr_id)
        self.__completion_strategy = completion_strategy
        self.__timestamp = timestamp

    @property
    def completion_strategy(self) -> str:
        return self.__completion_strategy

    @property
    def timestamp(self) -> float:
        return self.__timestamp

    def __str__(self):
        return super().__str__(completion_strategy=self.completion_strategy, timestamp=self.timestamp)


class CommandResponseEnvelope(DeviceEnvelope):
    def __init__(
            self,
            device: typing.Union[Device, str],
            service: str,
            message: DeviceMessage,
            corr_id: str
    ):
        super().__init__(device=device, service=service, message=message, corr_id=corr_id)


def response_from_command_envelope(message: DeviceMessage, envelope: CommandEnvelope) -> CommandResponseEnvelope:
    validate_instance(envelope, CommandEnvelope)
    return CommandResponseEnvelope(
        device=envelope.device_id,
        service=envelope.service_uri,
        message=message,
        corr_id=envelope.correlation_id
    )


class EventEnvelope(DeviceEnvelope):

    def __init__(self, device: typing.Union[Device, str], service: str, message: DeviceMessage):
        super().__init__(device=device, service=service, message=message)


class FogProcessesEnvelope(Envelope):

    __slots__ = ('__sub_topic',)

    def __init__(self, sub_topic: str, message: typing.Union[str, bytes]):
        super().__init__(message=message)
        validate_instance(sub_topic, str)
        self.__sub_topic = sub_topic

    @property
    def sub_topic(self) -> str:
        return self.__sub_topic

    @property
    def message(self) -> typing.Union[str, bytes]:
        return Envelope.message.fget(self)

    @message.setter
    def message(self, arg):
        validate_instance(arg, (str, bytes))
        Envelope.message.fset(self, arg)

