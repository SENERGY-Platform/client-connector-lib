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

__all__ = ('Service', )


from typing import Union, NoReturn


class Service:
    def __init__(self, uri: str, name: str = None, type: str = None, input: dict = None, output: dict = None):
        __class__.__checkType(uri, str)
        if type:
            __class__.__checkType(type, str)
        if name:
            __class__.__checkType(name, str)
        if input:
            __class__.__checkType(input, dict)
        if output:
            __class__.__checkType(output, dict)
        self.__uri = uri
        self.__type = type
        self.__name = name
        self.__input = input
        self.__output = output
        self.__description = None

    @property
    def uri(self) -> str:
        return self.__uri

    @property
    def type(self) -> str:
        return self.__type

    @property
    def name(self) -> str:
        return self.__name

    @property
    def input(self) -> Union[dict, NoReturn]:
        if self.__input:
            return self.__input.copy()

    @property
    def output(self) -> Union[dict, NoReturn]:
        if self.__output:
            return self.__output.copy()

    @property
    def description(self) -> str:
        return self.__description

    @description.setter
    def description(self, text: str):
        __class__.__checkType(text, str)
        self.__description = text

    @staticmethod
    def __checkType(arg, typ):
        """
        Check if arg is the correct type. Raise exception if not.
        :param: arg: object to check
        :param: typ: type
        """
        if type(arg) is not typ:
            raise TypeError("'{}' must be '{}' but is '{}'".format(arg, type(typ).__name__, type(arg)))

    def __repr__(self, **kwargs):
        """
        Provide a string representation.
        :param kwargs: User attributes provided from subclass.
        :return: String.
        """
        attributes = [
            ('uri', self.uri),
            ('type', self.type),
            ('input', self.input),
            ('output', self.output),
            ('description', self.description)
        ]
        if kwargs:
            for arg, value in kwargs.items():
                attributes.append((arg, value))
        return "{}({})".format(type(self).__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
