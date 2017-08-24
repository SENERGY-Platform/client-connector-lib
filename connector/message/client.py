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


class _Listen:
    def __init__(self, device):
        self.device = device

    @staticmethod
    def _serialize(message):
        return json.dumps([message.device.id])


class _Add:
    def __init__(self, device):
        self.device = device

    @staticmethod
    def _serialize(message):
        return json.dumps([{
            'uri': message.device.id,
            'connector_type': message.device.type,
            'name': message.device.name
        }])


class _Update:
    def __init__(self, device):
        self.device = device

    @staticmethod
    def _serialize(message):
        return json.dumps({
            'device_uri': message.device.id,
            'name': message.device.name
        })


class _Remove:
    def __init__(self, device):
        self.device = device

    @staticmethod
    def _serialize(message):
        pass


class _Mute:
    def __init__(self, device):
        self.device = device

    @staticmethod
    def _serialize(message):
        pass


_client_msg_prefix = {
    Response: 'response',
    Event: 'event',
    _Listen: 'listen_to_devices',
    _Add: 'add_devices',
    _Update: 'update_device_name',
    _Remove: 'remove_devices',
    _Mute: ''
}