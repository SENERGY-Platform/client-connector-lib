if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json

logger = root_logger.getChild(__name__)


class Message:
    _device_id_key = 'device_url'
    _endpoint_key = 'service_url'
    _payload_key = 'protocol_parts'

    def __init__(self):
        self._device_id = str()       # device_url
        self._endpoint = str()        # service_url (sepl)
        self._payload_header = str()  # protocol_parts
        self._payload = str()         # protocol_parts

    @property
    def device_id(self):
        return self._device_id

    @device_id.setter
    def device_id(self, arg):
        if type(arg) is not str:
            raise TypeError("device id must be a string but got '{}'".format(type(arg)))
        self._device_id = arg

    @property
    def payload_header(self):
        return self._payload_header

    @payload_header.setter
    def payload_header(self, arg):
        if type(arg) is not str:
            raise TypeError("payload header must be a string but got '{}'".format(type(arg)))
        self._payload_header = arg

    @property
    def payload(self):
        return self._payload

    @payload.setter
    def payload(self, arg):
        if type(arg) is not str:
            raise TypeError("payload body must be a string but got '{}'".format(type(arg)))
        self._payload = arg

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, arg):
        if self._timestamp:
            raise TypeError('attribute timestamp already set')
        else:
            if type(arg) is not int:
                raise TypeError("timestamp must be an integer but got '{}'".format(type(arg)))
            self._timestamp = arg

    @property
    def endpoint(self):
        return self._endpoint

    @endpoint.setter
    def endpoint(self, arg):
        raise TypeError('attribute endpoint is immutable')


    @staticmethod
    def pack(message):
        if type(message) is not Message:
            raise TypeError("message must be of type 'Message' but got '{}'".format(type(message)))
        payload = list()
        if message._payload_header:
            payload.append(
                {
                    'name': 'header',
                    'value': message._payload_header
                }
            )
        if message._payload:
            payload.append(
                {
                    'name': 'body',
                    'value': message._payload
                }
            )
        msg_struct = {
            Message._device_id_key: message._device_id,
            Message._endpoint_key: message._endpoint,
            Message._payload_key: payload,
        }
        msg_str = json.dumps(msg_struct)
        return msg_str

    @staticmethod
    def unpack(message):
        msg_obj = Message()
        try:
            message = json.loads(message)
            msg_obj._device_id = message.get(Message._device_id_key)
            msg_obj._endpoint = message.get(Message._endpoint_key)
            payload = message.get(Message._payload_key)
            for item in payload:
                part = item.get('name')
                if part == 'body':
                    msg_obj._payload = item.get('value')
                elif part == 'header':
                    msg_obj._payload_header = item.get('value')
        except Exception as ex:
            logger.error(ex)
        return msg_obj

class Prefix:
    change = 'change:'
    response = 'response:'
    update = 'update:'
