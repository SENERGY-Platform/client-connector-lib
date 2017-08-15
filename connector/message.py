if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json


logger = root_logger.getChild(__name__)


_device_id_key = 'device_url'
_service_key = 'service_url'
_value_key = 'protocol_parts'


class Payload:
    def __init__(self, header=None, body=None):
        self.__header = header or str()
        self.__body = body or str()

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
    def __init__(self, payload):
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


class ConnectorMsg:
    class Command(Message):
        def __init__(self, device_id, payload, endpoint):
            super().__init__(payload)
            self.__device_id = device_id             # device_uri
            self.__endpoint = endpoint               # service_uri (sepl)
            self.__overhead = None

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
            raise TypeError('attribute endpoint is immutable')


    class Response(Message):
        def __init__(self, payload):
            super().__init__(payload)


    class Error(Message):
        def __init__(self, payload):
            super().__init__(payload)


class ClientMsg:
    class ClientResponse():
        def __init__(self, comm_msg: ConnectorMsg.Command):
            if type(comm_msg) is not ConnectorMsg.Command:
                raise TypeError("response must be of type 'Command' but got '{}'".format(type(comm_msg)))
            self.__comm_msg = comm_msg

        def __getattr__(self, attr):
            return getattr(self.__comm_msg, attr)


    class ClientEvent(Message):
        def __init__(self, device_id, payload, endpoint):
            super().__init__(payload)
            self.__device_id = device_id             # device_uri
            self.__endpoint = endpoint               # service_uri (sepl)

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





def serializeMessage(message: Message):
    if type(message) is not Message:
        raise TypeError("message must be of type 'Message' but got '{}'".format(type(message)))
    if not message.device_id:
        raise ValueError('device id missing')
    value = (
        {
            'name': 'header',
            'value': message.payload.header
        },
        {
            'name': 'body',
            'value': message.payload.body
        }
    )
    msg = {
        _device_id_key: message.device_id,
        _service_key: message.endpoint,
        _value_key: value,
    }
    if message._Message__overhead:
        msg.update(message._Message__overhead)
    return json.dumps(msg)


def serializeMessageOld(message: Message):
    if type(message) is not Message:
        raise TypeError("message must be of type 'Message' but got '{}'".format(type(message)))
    if not message.device_id:
        raise ValueError('device id missing')
    protocol_parts = (
        {
            'name': 'header',
            'value': message.payload.header
        },
        {
            'name': 'body',
            'value': message.payload.body
        }
    )
    msg_struct = {
        _device_id_key: message.device_id,
        _service_key: message.endpoint,
        _value_key: protocol_parts,
    }
    msg_struct.update(message._Message__overhead)
    return json.dumps(msg_struct)


def deserializeMessage(message) -> Message:
    try:
        message = json.loads(message)
    except Exception as ex:
        logger.error(ex)
    payload = Payload()
    value = message.get(_value_key)
    for part in value:
        name = part.get('name')
        if name == 'body':
            payload.body = part.get('value')
        elif name == 'header':
            payload.header = part.get('value')
    msg_obj = Message(message.get(_device_id_key), payload, message.get(_service_key))
    message[_value_key] = None
    message[_device_id_key] = None
    message[_service_key] = None
    msg_obj._Message__overhead = message
    return msg_obj