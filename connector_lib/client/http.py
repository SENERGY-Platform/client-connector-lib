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

try:
    from .logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import urllib.request, certifi
from typing import Union, Iterable, IO


logger = root_logger.getChild(__name__.split('.', 1)[-1])


class Method:
    head = "HEAD"
    get = "GET"
    post = "POST"
    put = "PUT"
    delete = "DELETE"
    options = "OPTIONS"


class Response:
    def __init__(self, status, body=None, headers=None):
        self.__headers = headers
        self.__body = body
        self.__status = status

    @property
    def body(self):
        return self.__body

    @property
    def headers(self):
        return self.__headers

    @property
    def status(self):
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

    def __bool__(self):
        if self.__status:
            return True
        return False


class Request:
    def __init__(self, url: str, method: str = Method.get, data: Union[Iterable, IO, bytes] = None, headers: dict = None, timeout: int = 10):
        self.__url = url
        self.__method = method
        self.__data = data
        self.__headers = headers or dict()
        self.__timeout = timeout
        try:
            self.__request = urllib.request.Request(
                self.__url,
                data=self.__data,
                headers=self.__headers,
                method=self.__method
            )
        except Exception as ex:
            logger.error(ex)

    def send(self) -> Response:
        try:
            resp = urllib.request.urlopen(
                self.__request,
                timeout=self.__timeout,
                cafile=certifi.where(),
                context=None
            )
            return Response(
                status=resp.getcode(),
                body=resp.read().decode(),
                headers=dict(resp.info().items())
            )
        except Exception as ex:
            logger.error(ex)
        return Response(None)

    def __repr__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('url', self.__url),
            ('method', self.__method),
            ('data', self.__data),
            ('headers', self.__headers),
            ('timeout', self.__timeout)
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
