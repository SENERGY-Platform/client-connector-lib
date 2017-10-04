if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json
from uuid import uuid4 as uuid


logger = root_logger.getChild(__name__)


handlers = {
    'put_handler': 'put',
    'mute_handler': 'mute',
    'event_handler': 'event',
    'response_handler': 'response',
    'command_handler': 'command'
}


class Message:
    def __init__(self, handler=None, msg=None):
        self.__status = int()
        self.__handler = handler or str()
        self.__token = str()
        self.__content_type = str()
        self.__payload = None
        if msg:
            try:
                msg = json.loads(msg)
                for key in msg:
                    setattr(self, '_{}__{}'.format(self.__class__.__name__, key), msg[key])
            except Exception as ex:
                logger.error("malformed message: '{}'".format(msg))
                logger.debug(ex)
        else:
            self.__token = str(uuid())

    def __str__(self):
        return json.dumps({key.replace('_{}__'.format(__class__.__name__), ''): self.__dict__[key] for key in self.__dict__})

    @property
    def status(self):
        return self.__status

    #@status.setter
    #def status(self, arg):
    #    if type(arg) is not int:
    #        raise TypeError("status must be integer but got '{}'".format(type(arg)))
    #    self.__status = arg

    @property
    def content_type(self):
        return self.__content_type

    @property
    def payload(self):
        return self.__payload

    @payload.setter
    def payload(self, arg):
        if type(arg) not in (int, str, dict, list, bool, float, type(None)):
            raise TypeError("unsupported type '{}' provided for payload".format(type(arg)))
        self.__payload = arg


'''
class Event(_Message):
    def __init__(self, device, service, payload):
        if type(device) is Device:
            d_id = device.id
        elif type(device) is str:
            d_id = device
        else:
            raise TypeError("device must be string or Device but got '{}'".format(type(device)))
        if type(service) is not str:
            raise TypeError("service must be string but got '{}'".format(type(service)))
        #if type(payload) is not str:
        #    raise TypeError("payload must be string but got '{}'".format(type(payload)))
        msg = {
            'device_uri': d_id,
            'service_uri': service,
            'value': [
                {
                    'name': 'body',
                    'value': payload
                }
            ]
        }
        super().__init__()
        self.__handler = _handlers[__class__]
        self.payload = msg


class _Command(_Message):
    def __init__(self):
        super().__init__()

    def createResponse(self, payload):
        response = _Response()
        setattr(response, '_{}__token'.format(response.__class__.__name__), self.__token)
        response.payload = payload
        return response


class _Put(_Message):
    def __init__(self):
        super().__init__()
        self.__handler = _handlers[__class__]


class _Mute(_Message):
    def __init__(self):
        super().__init__()
        self.__handler = _handlers[__class__]


class _Response(_Message):
    def __init__(self):
        super().__init__()
        self.__handler = _handlers[__class__]
'''



#test_msg = json.dumps({"status":200,"handler":"response","token":"credentials","content_type":"map","payload":{"gid":"iot#d1608369-bdb1-45d6-8d82-78bbc59b5311","hash":""}})

#test = Message(test_msg)
#print(getattr(test, '_{}__token'.format(test.__class__.__name__)))
#setattr(test, '_{}__handler'.format(test.__class__.__name__), 'bs')
