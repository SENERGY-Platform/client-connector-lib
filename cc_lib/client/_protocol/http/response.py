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


import typing


class Response:
    def __init__(self, status: int, body: typing.Optional[str] = None, headers: typing.Optional[dict] = None):
        self.__headers = headers
        self.__body = body
        self.__status = status

    @property
    def body(self) -> typing.Optional[str]:
        return self.__body

    @property
    def headers(self) -> typing.Optional[dict]:
        return self.__headers

    @property
    def status(self) -> int:
        return self.__status

    def __repr__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('body', self.__body),
            ('header', self.__headers),
            ('status', self.__status)
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
