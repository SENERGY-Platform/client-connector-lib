if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from connector.message.message import Message
    from connector.message.connector import Command
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json


logger = root_logger.getChild(__name__)


class Response():
    def __init__(self, comm_msg):
        if type(comm_msg) is not Command:
            raise TypeError("response must be of type 'Command' but got '{}'".format(type(comm_msg)))
        self.__comm_msg = comm_msg

    def __getattr__(self, attr):
        return getattr(self.__comm_msg, attr)

    @staticmethod
    def _serialize(message):
        message._overhead['protocol_parts'] = [
            {
                'name': 'header',
                'value': message.payload.header
            },
            {
                'name': 'body',
                'value': message.payload.body
            }
        ]
        return json.dumps(message._overhead)


class Event(Message):
    def __init__(self, device_id=None, endpoint=None):
        super().__init__()
        self.__device_id = device_id
        self.__endpoint = endpoint

    @property
    def device_id(self):
        return self.__device_id

    @device_id.setter
    def device_id(self, arg):
        if type(arg) is not str:
            raise TypeError("device id must be a string but got '{}'".format(type(arg)))
        self.__device_id = arg

    @property
    def endpoint(self):
        return self.__endpoint

    @endpoint.setter
    def endpoint(self, arg):
        if type(arg) is not str:
            raise TypeError("device id must be a string but got '{}'".format(type(arg)))
        self.__endpoint = arg

    @staticmethod
    def _serialize(message):
        msg = {
            'device_uri': message.device_id,
            'service_uri': message.endpoint,
            'value': [
                {
                    'name': 'header',
                    'value': message.payload.header
                },
                {
                    'name': 'body',
                    'value': message.payload.body
                }
            ]
        }
        return json.dumps(msg)


_client_msg_prefix = {
    Response: 'response',
    Event: 'event'
}