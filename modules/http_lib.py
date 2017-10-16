if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time
from socket import timeout as Timeout
from urllib import parse
from urllib import request as http


logger = root_logger.getChild(__name__)


def build_request(methode, url, body=None, query={}, headers={}):
    if query:
        parsed_url = list(parse.urlparse(url))
        parsed_url[4] = parse.urlencode(query)
        url = parse.urlunparse(tuple(parsed_url))
    if body:
        body = body.encode('utf-8')
    return http.Request(method=methode, url=url, data=body, headers=headers)


class Response:
    def __init__(self, request, timeout=3, retries=0, retry_delay=0.5):
        self.__request = request
        self._body = None
        self._header = None
        self._status = None
        for req in range(1+retries):
            try:
                response = http.urlopen(self.__request, timeout=timeout)
                self._body = response.read().decode('utf-8')
                self._header = dict(response.info().items())
                self._status = response.getcode()
                logger.debug("{}: {} - {}".format(self.__request.method, self.__request.full_url, self._status))
                break
            except http.HTTPError as ex:
                self._body = ex.reason
                self._header = dict(ex.headers.items())
                self._status = ex.code
                logger.error("{}: {} - {}".format(self.__request.method, self.__request.full_url, self._status))
            except Timeout:
                logger.error("{}: {} - {}".format(self.__request.method, self.__request.full_url, 'timed out'))
            except Exception as ex:
                logger.error("{}: {} - {}".format(self.__request.method, self.__request.full_url, ex))
            time.sleep(retry_delay)

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, arg):
        raise TypeError('object does not support item assignment')

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, arg):
        raise TypeError('object does not support item assignment')

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, arg):
        raise TypeError('object does not support item assignment')


class Methods:
    @staticmethod
    def get(url, query={}, headers={}, **kwargs):
        request = build_request("GET", url, query=query, headers=headers)
        return Response(request, **kwargs)

    @staticmethod
    def post(url, body, headers={}, **kwargs):
        request = build_request("POST", url, body, headers=headers)
        return Response(request, **kwargs)

    @staticmethod
    def put(url, body, headers={}, **kwargs):
        request = build_request("PUT", url, body, headers=headers)
        return Response(request, **kwargs)

    @staticmethod
    def delete(url, headers={}, **kwargs):
        request = build_request("DELETE", url, headers=headers)
        return Response(request, **kwargs)

    @staticmethod
    def header(url, query={}, headers={}, **kwargs):
        request = build_request("HEADER", url, query=query, headers=headers)
        return Response(request, **kwargs)