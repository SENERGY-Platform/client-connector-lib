if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))


logger = root_logger.getChild(__name__)


class Payload:
    def __init__(self):
        self.__header = str()
        self.__body = str()

    @property
    def header(self):
        return self.__header

    @header.setter
    def header(self, arg):
        if type(arg) is not str:
            raise TypeError("payload header must be a string but got '{}'".format(type(arg)))
        self.__header = arg

    @property
    def body(self):
        return self.__body

    @body.setter
    def body(self, arg):
        if type(arg) is not str:
            raise TypeError("payload body must be a string but got '{}'".format(type(arg)))
        self.__body = arg


class Message:
    def __init__(self, payload=None):
        if payload and type(payload) is not Payload:
            raise TypeError("payload must be of type 'Payload' but got '{}'".format(type(payload)))
        self.__payload = payload or Payload()    # value
        self._token = None

    @property
    def payload(self):
        return self.__payload

    @payload.setter
    def payload(self, arg):
        raise TypeError("attribute payload is immutable, use 'payload.body' or 'payload.header' instead")
