if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

logger = root_logger.getChild(__name__)


class Device():
    def __init__(self, d_id, d_type, d_name):
        self.id = d_id
        self.type = d_type
        self.name = d_name
