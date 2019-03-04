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

__all__ = ('Method', 'ContentType', 'Request')


from ....logger.logger import getLogger
from .response import Response
import urllib.request, urllib.parse, json
from typing import Union, Iterable, SupportsAbs


logger = getLogger(__name__.split('.', 1)[-1])


ca_file = None

try:
    import certifi
    ca_file = certifi.where()
except ImportError as ex:
    pass


class Method:
    head = "HEAD"
    get = "GET"
    post = "POST"
    put = "PUT"
    delete = "DELETE"
    options = "OPTIONS"


class ContentType:
    json = 'application/json'
    form = 'application/x-www-form-urlencoded'
    plain = 'text/plain'


class Request:
    def __init__(self, url: str, method: str = Method.get, body: Union[Iterable, SupportsAbs] = None, content_type: str = None, headers: dict = None, timeout: int = 10):
        self.__url = url
        self.__method = method
        self.__body = body
        self.__headers = headers or dict()
        self.__timeout = timeout
        self.__request = None
        try:
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
                    raise RuntimeError('unsupported content type for body')
                self.__headers['content-type'] = content_type
            self.__request = urllib.request.Request(
                self.__url,
                data=self.__body,
                headers=self.__headers,
                method=self.__method
            )
        except Exception as ex:
            logger.error(ex)

    def send(self) -> Response:
        if self.__request:
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
            except urllib.request.HTTPError as ex:
                return Response(
                    status=ex.code,
                    body=ex.reason,
                    headers=dict(ex.headers.items())
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
            ('body', self.__body),
            ('headers', self.__headers),
            ('timeout', self.__timeout)
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))
