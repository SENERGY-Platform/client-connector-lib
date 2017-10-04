if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
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


def getMangledAttr(obj, attr):
    return getattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr))


def setMangledAttr(obj, attr, arg):
    setattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr), arg)


def marshalMsg(msg_obj):
    return json.dumps({key.replace('_{}__'.format(msg_obj.__class__.__name__), ''): msg_obj.__dict__[key] for key in msg_obj.__dict__})


def unmarshalMsg(msg_str):
    try:
        msg = json.loads(msg_str)
        msg_obj = Message()
        for key in msg:
            setMangledAttr(msg_obj, key, msg[key])
        return msg_obj
    except Exception as ex:
        logger.error("malformed message: '{}'".format(msg_str))
        logger.debug(ex)


class Message:
    def __init__(self, handler=str()):
        self.__status = int()
        self.__handler = handler
        self.__token = str(uuid())
        self.__content_type = str()
        self.__payload = None

    @property
    def status(self):
        return self.__status

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


#test_msg = json.dumps({"status":200,"handler":"response","token":"credentials","content_type":"map","payload":{"gid":"iot#d1608369-bdb1-45d6-8d82-78bbc59b5311","hash":""}})

#test = unmarshalMsg(test_msg)
#print(getattr(test, '_{}__token'.format(test.__class__.__name__)))
#setattr(test, '_{}__handler'.format(test.__class__.__name__), 'bs')
#print(marshalMsg(test))
