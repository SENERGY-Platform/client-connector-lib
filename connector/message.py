if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json


logger = root_logger.getChild(__name__)


class _Payload:
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


class _Message:
    def __init__(self, payload=None):
        if payload and type(payload) is not _Payload:
            raise TypeError("payload must be of type '_Payload' but got '{}'".format(type(payload)))
        self.__payload = payload or _Payload()    # value
        self._token = None

    @property
    def payload(self):
        return self.__payload

    @payload.setter
    def payload(self, arg):
        raise TypeError("attribute payload is immutable, use 'payload.body' or 'payload.header' instead")


class ConnectorMsg:
    class Command(_Message):
        def __init__(self, com_msg):
            try:
                com_msg = json.loads(com_msg)
            except Exception as ex:
                logger.error(ex)
            payload = _Payload()
            value = com_msg.get('protocol_parts')
            for part in value:
                name = part.get('name')
                if name == 'body':
                    payload.body = part.get('value')
                elif name == 'header':
                    payload.header = part.get('value')
            super().__init__(payload)
            self.__device_id = com_msg.get('device_url')
            self.__service = com_msg.get('service_url')
            self._overhead = com_msg

        @property
        def device_id(self):
            return self.__device_id

        @device_id.setter
        def device_id(self, arg):
            raise TypeError('device id is immutable')

        @property
        def service(self):
            return self.__service

        @service.setter
        def service(self, arg):
            raise TypeError('attribute service is immutable')


    class Response(_Message):
        def __init__(self, res_msg):
            payload = _Payload()
            payload.body = res_msg
            super().__init__(payload)


    class Error(_Message):
        def __init__(self, err_msg):
            payload = _Payload()
            payload.body = err_msg
            super().__init__(payload)


    _prefix_map = {
        'command': Command,
        'response': Response,
        'error': Error
    }


class ClientMsg:
    class Response():
        def __init__(self, comm_msg):
            if type(comm_msg) is not ConnectorMsg.Command:
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


    class Event(_Message):
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


    _prefix_map = {
        Response: 'response',
        Event: 'event'
    }
