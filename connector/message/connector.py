if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from connector.message.message import Message, Payload
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json


logger = root_logger.getChild(__name__)



class Command(Message):
    def __init__(self, com_msg):
        try:
            com_msg = json.loads(com_msg)
        except Exception as ex:
            logger.error(ex)
        payload = Payload()
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


class Response(Message):
    def __init__(self, res_msg):
        payload = Payload()
        payload.body = res_msg
        super().__init__(payload)


class Error(Message):
    def __init__(self, err_msg):
        payload = Payload()
        payload.body = err_msg
        super().__init__(payload)


connector_msg_obj = {
    'command': Command,
    'response': Response,
    'error': Error
}