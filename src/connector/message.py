if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json, time

logger = root_logger.getChild(__name__)


class Message:
    _device_id_key = 'device_url'
    _service_key = 'service_url'
    _time_stamp_key = 'time'
    _task_id_key = 'task_id'
    _data_key = 'protocol_parts'
    _payload_key = 'value'

    def __init__(self):
        self.device_id = None
        self.service = None
        self.time_stamp = None
        self.task_id = None
        self.payload = None

    @staticmethod
    def pack(message):
        if type(message) is not Message:
            raise TypeError("message must be of type 'Message' but got '{}'".format(type(message)))
        message.time_stamp = int(time.mktime(time.localtime()))
        # build message string/json:
        str_message = message.payload # ask ingo about message format
        return str_message

    @staticmethod
    def unpack(message):
        msg_obj = Message()
        try:
            message = json.loads(message)
            msg_obj.device_id = message.get(Message._device_id_key)
            msg_obj.service = message.get(Message._service_key)
            msg_obj.time_stamp = message.get(Message._time_stamp_key)
            msg_obj.task_id = message.get(Message._task_id_key)
            data = message.get(Message._data_key)
            if len(data):
                payload_dirty = data[0].get(Message._payload_key)
                msg_obj.payload = payload_dirty.replace('\n', '').replace(' ', '')
        except Exception as ex:
            logger.error(ex)
        return msg_obj
