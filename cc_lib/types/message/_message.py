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


__all__ = ("DeviceMessage", )


from ..._util import validate_instance
import typing


class DeviceMessage:

    __slots__ = ('__metadata', '__data')

    def __init__(self, data: typing.Optional[str] = None, metadata: typing.Optional[str] = None):
        self.__metadata = metadata or str()
        self.__data = data or str()

    @property
    def metadata(self) -> str:
        return self.__metadata

    @metadata.setter
    def metadata(self, arg: str):
        validate_instance(arg, str)
        self.__metadata = arg

    @property
    def data(self) -> str:
        return self.__data

    @data.setter
    def data(self, arg: str):
        validate_instance(arg, str)
        self.__data = arg

    def __iter__(self):
        items = (('metadata', self.metadata), ('data', self.data))
        for item in items:
            yield item

    def __repr__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [('metadata', self.metadata), ('data', self.data)]
        return "{}({})".format(
            __class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes])
        )
