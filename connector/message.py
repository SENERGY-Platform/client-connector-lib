if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json
from uuid import uuid4 as uuid


logger = root_logger.getChild(__name__)

class Envelope:
    def __init__(self, handler, message, token):
        self.handler = handler
        self.token = token
        if type(message) is not Message:
            raise TypeError("message must be of type 'Message' but got '{}'".format(type(message)))
        self.message = message

    @staticmethod
    def open(string: str):
        handler_and_token, message = string.split(':', maxsplit=1)
        #### temp ####
        if '.' in handler_and_token:
            handler, token = handler_and_token.split('.', maxsplit=1)
            return __class__(handler, Message.deserialize(message), token)
        else:
            handler = handler_and_token
            return __class__(handler, Message.deserialize(message), uuid())
        #### temp ####

    @staticmethod
    def close(envelope):
        return '{}.{}:{}'.format(envelope.handler, envelope.token, Message.serialize(envelope.message))


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
    _device_id_key = 'device_url'
    _service_key = 'service_url'
    _protocol_parts_key = 'protocol_parts'

    def __init__(self, device_id, payload=None, endpoint=None):
        self.__device_id = device_id             # device_url
        self.__endpoint = endpoint               # service_url (sepl)
        if type(payload) is not Payload:
            raise TypeError("payload must be of type 'Payload' but got '{}'".format(type(payload)))
        self.__payload = payload or Payload()                 # protocol_parts
        self.__token = 123
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
    def payload(self):
        return self.__payload

    @payload.setter
    def payload(self, arg):
        raise TypeError("attribute payload is immutable, use 'payload.body' or 'payload.header' instead")

    @property
    def endpoint(self):
        return self.__endpoint

    @endpoint.setter
    def endpoint(self, arg):
        raise TypeError('attribute endpoint is immutable')

    @staticmethod
    def serialize(message: __class__):
        if type(message) is not Message:
            raise TypeError("message must be of type 'Message' but got '{}'".format(type(message)))
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
            Message._device_id_key: message.device_id,
            Message._service_key: message.endpoint,
            Message._protocol_parts_key: protocol_parts,
        }
        ### temp ###
        msg_struct.update(message.__overhead)
        ### temp ###
        return json.dumps(msg_struct)

    @staticmethod
    def deserialize(message) -> __class__:
        try:
            message = json.loads(message)
        except Exception as ex:
            logger.error(ex)
        payload = Payload()
        protocol_parts = message.get(Message._protocol_parts_key)
        for part in protocol_parts:
            name = part.get('name')
            if name == 'body':
                payload.body = part.get('value')
            elif name == 'header':
                payload.header = part.get('value')
        msg_obj = __class__(message.get(Message._device_id_key), payload, message.get(Message._service_key))
        #### temp ####
        del message[Message._protocol_parts_key]
        del message[Message._device_id_key]
        del message[Message._service_key]
        msg_obj.__overhead = message
        #### temp ####
        return msg_obj
