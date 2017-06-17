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
    _endpoint_name_key = 'service_name'
    _timestamp_key = 'time'
    _task_id_key = 'task_id'
    _payload_key = 'protocol_parts'
    _instance_id_key = 'device_instance_id'
    _worker_id_key = 'worker_id'
    _output_name_key = 'output_name'

    def __init__(self):
        self._device_id = str()       # device_url
        self._endpoint = str()        # service_url (sepl)
        self._endpoint_name = str()   # service_name (sepl)
        self._timestamp = int()       # time (sepl)
        self._task_id = str()         # task_id (sepl)
        self._instance_id = str()     # device_instance_id (sepl)
        self._worker_id = str()       # worker_id (sepl)
        self._output_name = str()     # output_name (sepl)
        self._payload_header = str()  # protocol_parts
        self._payload = str()    # protocol_parts

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
        raise TypeError('attribute timestamp is immutable')

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
            Message._endpoint_name_key: message._endpoint_name,
            Message._timestamp_key: str(message._timestamp),
            Message._task_id_key: message._task_id,
            Message._payload_key: payload,
            Message._instance_id_key: message._instance_id,
            Message._worker_id_key: message._worker_id,
            Message._output_name_key: message._output_name
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
            msg_obj._endpoint_name = message.get(Message._endpoint_name_key)
            msg_obj._timestamp = int(message.get(Message._timestamp_key))
            msg_obj._task_id = message.get(Message._task_id_key)
            msg_obj._instance_id = message.get(Message._instance_id_key)
            msg_obj._worker_id = message.get(Message._worker_id_key)
            msg_obj._output_name = message.get(Message._output_name_key)
            payload = message.get(Message._payload_key)
            for item in payload:
                value_dirty = item.get('value')
                part = item.get('name')
                if part == 'body':
                    msg_obj._payload = value_dirty.replace('\n', '').replace(' ', '')
                elif part == 'header':
                    msg_obj._payload_header = value_dirty.replace('\n', '').replace(' ', '')
        except Exception as ex:
            logger.error(ex)
        return msg_obj

class Prefix:
    change = 'change:'
    response = 'response:'
    update = 'update:'
