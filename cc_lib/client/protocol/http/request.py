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

__all__ = ('urlEncode', 'Method', 'ContentType', 'Request', 'URLError', 'SocketTimeout')


from ....logger import getLogger
from .response import Response
from typing import Union, Iterable, SupportsAbs, Optional
from socket import timeout as SocketTimeout
from urllib.error import URLError, HTTPError
import urllib.request
import urllib.parse
import json


logger = getLogger(__name__.split('.', 1)[-1])


ca_file = None

try:
    import certifi
    ca_file = certifi.where()
except ImportError as ex:
    pass


reserved_chars = {
    "!": "%21",
    "#": "%23",
    "$": "%24",
    "&": "%26",
    "'": "%27",
    "(": "%28",
    ")": "%29",
    "*": "%2A",
    "+": "%2B",
    ",": "%2C",
    "/": "%2F",
    ":": "%3A",
    ";": "%3B",
    "=": "%3D",
    "?": "%3F",
    "@": "%40",
    "[": "%5B",
    "]": "%5D"
}


def urlEncode(s: str) -> str:
    """
    Encode string to URL encoded format.
    :param s: String to encode.
    :return: Encoded string.
    """
    for char, perc_enc in reserved_chars.items():
        s = s.replace(char, perc_enc)
    return s


class Method:
    HEAD = "HEAD"
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"


class ContentType:
    json = 'application/json'
    form = 'application/x-www-form-urlencoded'
    plain = 'text/plain'


class Request:
    def __init__(self, url: str, method: str = Method.GET, body: Optional[Union[Iterable, SupportsAbs]] = None, content_type: Optional[str] = None, headers: Optional[dict] = None, timeout: int = 30):
        self.__url = url
        self.__method = method
        self.__body = body
        self.__headers = headers or dict()
        self.__timeout = timeout
        self.__request = None
        if self.__body and not content_type:
            raise RuntimeError('missing content type for body')
        if self.__body and content_type:
            if content_type == ContentType.json:
                self.__body = json.dumps(self.__body).encode()
            elif content_type == ContentType.form:
                self.__body = urllib.parse.urlencode(self.__body).encode()
            elif content_type == ContentType.plain:
                if type(self.__body) not in (int, float, complex, str):
                    logger.warning("body with none primitive type '{}' will be converted to string representation".format(type(body).__name__))
                self.__body = str(self.__body).encode()
            else:
                raise RuntimeError("unsupported content type '{}'".format(content_type))
            self.__headers['content-type'] = content_type
        self.__request = urllib.request.Request(
            self.__url,
            data=self.__body,
            headers=self.__headers,
            method=self.__method
        )

    def send(self) -> Response:
        try:
            resp = urllib.request.urlopen(
                self.__request,
                timeout=self.__timeout,
                cafile=ca_file,
                context=None
            )
            return Response(
                status=resp.getcode(),
                body=resp.read().decode(),
                headers=dict(resp.info().items())
            )
        except HTTPError as ex:
            return Response(
                status=ex.code,
                body=ex.reason,
                headers=dict(ex.headers.items())
            )
        except URLError as ex:
            logger.error("{} - '{}'".format(ex, self.__url))
            raise
        except SocketTimeout:
            logger.error("timed out - '{}' - {}".format(self.__url, self.__method))
            raise

    def __repr__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('url', self.__url),
            ('method', self.__method),
            ('body', self.__body),
            ('headers', self.__headers),
            ('timeout', self.__timeout)
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
