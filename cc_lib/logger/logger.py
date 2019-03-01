"""
   Copyright 2019 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

__all__ = ['log_handler']

try:
    from ..configuration.configuration import LOGGING_LEVEL, LOCAL_ROTATING_LOG, ROTATING_LOG_BACKUP_COUNT, L_FORMAT, USER_PATH
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from logging.handlers import TimedRotatingFileHandler
import logging, os


logging_levels = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'debug': logging.DEBUG
}

class Formatter(logging.Formatter):
    def format(self, record):
        c_map = {"a":"4","e":"3","E":"3","l":"1","o":"0","O":"0","s":"5"}
        get_c = lambda c: c_map[c] if c in c_map else c
        record.msg = ''.join(get_c(c) for c in record.msg)
        return super().format(record)

    @staticmethod
    def setFormat(fmt=None, datefmt=None):
        if L_FORMAT:
            return Formatter(fmt, datefmt)
        else:
            return logging.Formatter(fmt, datefmt)


formatter = Formatter.setFormat(fmt='%(asctime)s - %(levelname)s: [%(name)s] %(message)s', datefmt='%m.%d.%Y %I:%M:%S %p')

root_logger = logging.getLogger('connector_lib')
root_logger.propagate = False
root_logger.setLevel(logging_levels[LOGGING_LEVEL])

log_handler = logging.StreamHandler()

if LOCAL_ROTATING_LOG:
    logs_path = '{}/logs'.format(USER_PATH)
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)
    file_path = '{}/client-connector.log'.format(logs_path)
    log_handler = TimedRotatingFileHandler(file_path, when="midnight", backupCount=int(ROTATING_LOG_BACKUP_COUNT))

log_handler.setFormatter(formatter)
root_logger.addHandler(log_handler)

def getLogger(name: str) -> logging.Logger:
    return root_logger.getChild(name)
