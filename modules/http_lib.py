if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time, base64
from socket import timeout as Timeout
from urllib import parse
from urllib import request as http


logger = root_logger.getChild(__name__)


class Request:
    def __init__(self, method, url, body=None, query=None, headers=None, auth=None):
        parsed_url = list(parse.urlparse(url))
        #self.__handlers = list()
        if body:
            if type(body) is not str:
                raise TypeError("body must be string - got '{}'".format(type(body)))
            body = body.encode('utf-8')
        if query:
            if type(query) is not dict:
                raise TypeError("query must be dict - got '{}'".format(type(query)))
            parsed_url[4] = parse.urlencode(query)
        if headers and type(headers) is not dict:
            raise TypeError("headers must be dict - got '{}'".format(type(headers)))
        if auth:
            if type(auth) is not tuple:
                raise TypeError("auth must be tuple ('usr', 'pw') - got '{}'".format(type(auth)))
            """
            usr, pw = auth
            auth_handler = http.HTTPBasicAuthHandler()
            auth_handler.add_password(
                realm=None,
                uri=parse.urlunparse((parsed_url[0], parsed_url[1], '', '', '', '')),
                user=usr,
                passwd=pw
            )
            self.__handlers.append(auth_handler)
            """
            base64credentials = base64.b64encode('{}:{}'.format(*auth).encode()).decode()
            if not headers:
                headers = {'Authorization': 'Basic {}'.format(base64credentials)}
            else:
                headers['Authorization'] = 'Basic {}'.format(base64credentials)
        self.__method = method
        self.__url = parse.urlunparse(tuple(parsed_url))
        #self.__opener = http.build_opener(*self.__handlers)
        self.__request = http.Request(method=self.__method, url=self.__url, data=body, headers=headers or dict())

    def execute(self, timeout):
        #return self.__opener.open(self.__request, timeout=timeout)
        return http.urlopen(self.__request, timeout=timeout)

    @property
    def url(self):
        return self.__url

    @property
    def method(self):
        return self.__method


class Response:
    def __init__(self, request, timeout=10, retries=0, retry_delay=0.5):
        self.__body = None
        self.__header = None
        self.__status = None
        for retry in range(1+retries):
            try:
                response = request.execute(timeout)
                self.__body = response.read().decode('utf-8')
                self.__header = dict(response.info().items())
                self.__status = response.getcode()
                logger.debug("{}: {} - {}".format(request.method, request.url, self.__status))
                break
            except http.HTTPError as ex:
                self.__body = ex.reason
                self.__header = dict(ex.headers.items())
                self.__status = ex.code
                logger.error("{}: {} - {}".format(request.method, request.url, self.__status))
            except Timeout:
                logger.error("{}: {} - {}".format(request.method, request.url, 'timed out'))
            except Exception as ex:
                logger.error("{}: {} - {}".format(request.method, request.url, ex))
            time.sleep(retry_delay)

    @property
    def body(self):
        return self.__body

    @property
    def header(self):
        return self.__header

    @property
    def status(self):
        return self.__status


class Methods:
    @staticmethod
    def get(url, query=None, headers=None, auth=None, **kwargs):
        request = Request("GET", url, query=query, headers=headers, auth=auth)
        return Response(request, **kwargs)

    @staticmethod
    def post(url, body, headers=None, auth=None, **kwargs):
        request = Request("POST", url, body, headers=headers, auth=auth)
        return Response(request, **kwargs)

    @staticmethod
    def put(url, body, headers=None, auth=None, **kwargs):
        request = Request("PUT", url, body, headers=headers, auth=auth)
        return Response(request, **kwargs)

    @staticmethod
    def delete(url, headers=None, auth=None, **kwargs):
        request = Request("DELETE", url, headers=headers, auth=auth)
        return Response(request, **kwargs)

    @staticmethod
    def header(url, query=None, headers=None, auth=None, **kwargs):
        request = Request("HEADER", url, query=query, headers=headers, auth=auth)
        return Response(request, **kwargs)