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

__all__ = ('OpenIdClient', 'NoTokenError')

from ..logger.logger import _getLibLogger
from .protocol import http
from time import time as currentTimeStamp
import json


logger = _getLibLogger(__name__.split('.', 1)[-1])


class OpenIdException(Exception):
    pass


class RequestError(OpenIdException):
    pass


class ResponseError(OpenIdException):
    pass


class NoTokenError(OpenIdException):
    pass


class Token:
    def __init__(self, token, max_age):
        self.token = token
        self.max_age = max_age
        self.time_stamp = int(currentTimeStamp())


class OpenIdClient:
    def __init__(self, url, usr, pw, id):
        self.__url = url
        self.__usr = usr
        self.__pw = pw
        self.__id = id
        self.__access_token: Token = None
        self.__refresh_token: Token = None
        self.__token_type = None
        self.__not_before_policy = None
        self.__session_state = None

    def getAccessToken(self) -> str:
        try:
            if self.__access_token:
                if int(currentTimeStamp()) - self.__access_token.time_stamp >= self.__access_token.max_age:
                    logger.debug('access token expired')
                    if int(currentTimeStamp()) - self.__refresh_token.time_stamp >= self.__refresh_token.max_age:
                        logger.debug('refresh token expired')
                        self.__tokenRequest()
                    else:
                        self.__refreshRequest()
            else:
                self.__tokenRequest()
            return self.__access_token.token
        except (RequestError, ResponseError) as ex:
            raise NoTokenError(ex)

    def __setResponse(self, payload):
        try:
            payload = json.loads(payload)
            self.__access_token = Token(payload['access_token'], payload['expires_in'])
            self.__refresh_token = Token(payload['refresh_token'], payload['refresh_expires_in'])
            self.__token_type = payload['token_type']
            self.__not_before_policy = payload['not-before-policy']
            self.__session_state = payload['session_state']
        except (json.JSONDecodeError, KeyError) as ex:
            logger.error('malformed response - {}'.format(ex))
            raise ResponseError

    def __tokenRequest(self):
        payload = {
            'grant_type': 'password',
            'username': self.__usr,
            'password': self.__pw,
            'client_id': self.__id
        }
        req = http.Request(url=self.__url, method=http.Method.POST, body=payload, content_type=http.ContentType.form)
        try:
            resp = req.send()
            if resp.status == 200:
                self.__setResponse(resp.body)
            else:
                logger.error('token request got bad response - {}'.format(resp))
                raise RequestError
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error('token request failed - {}'.format(ex))
            raise RequestError

    def __refreshRequest(self):
        payload = {
            'grant_type': 'refresh_token',
            'client_id': self.__id,
            'refresh_token': self.__refresh_token.token
        }
        req = http.Request(url=self.__url, method=http.Method.POST, body=payload, content_type=http.ContentType.form)
        try:
            resp = req.send()
            if resp.status == 200:
                self.__setResponse(resp.body)
            else:
                logger.error('refresh request got bad response - {}'.format(resp))
                raise RequestError
        except (http.TimeoutErr, http.URLError) as ex:
            logger.error('refresh request failed - {}'.format(ex))
            raise RequestError
