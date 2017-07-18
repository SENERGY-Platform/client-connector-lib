try:
    from modules.logger import root_logger
    from modules.http_lib import Methods as http
    from connector.connector import Connector
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

logger = root_logger.getChild(__name__)


if __name__ == '__main__':
    connector = Connector()
