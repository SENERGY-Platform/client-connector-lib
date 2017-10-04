if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json


logger = root_logger.getChild(__name__)

class Message:
    def __init__(self, msg=None):
        super().__init__()
        self.__status = int()
        self.__handler = str()
        self.__token = str()
        self.__content_type = str()
        self.__payload = None
        if msg:
            msg = json.loads(msg)
            for key in msg:
                setattr(self, '_{}__{}'.format(__class__.__name__, key), msg[key])

    def __str__(self):
        return json.dumps({key.replace('_{}__'.format(__class__.__name__), ''): self.__dict__[key] for key in self.__dict__})

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, arg):
        if type(arg) is not int:
            raise TypeError("status must be integer but got '{}'".format(type(arg)))
        self.__status = arg

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


test_msg = json.dumps({"status":200,"handler":"response","token":"credentials","content_type":"map","payload":{"gid":"iot#d1608369-bdb1-45d6-8d82-78bbc59b5311","hash":""}})

test = Message(test_msg)
print(getattr(test, '_{}__token'.format(test.__class__.__name__)))
setattr(test, '_{}__handler'.format(test.__class__.__name__), 'bs')
