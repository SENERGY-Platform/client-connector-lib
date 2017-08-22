if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

logger = root_logger.getChild(__name__)


class Device():
    def __init__(self, id, type, name):
        self.id = id
        self.type = type
        self.name = name
