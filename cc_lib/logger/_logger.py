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

__all__ = ('getLogger', )

from .._configuration.configuration import user_dir, cc_conf
import os
import threading
import logging
import logging.handlers


lock = threading.RLock()


logging_levels = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'debug': logging.DEBUG
}

color_code = {
    'CRITICAL': '\033[41m',
    'ERROR': '\033[31m',
    'WARNING': '\033[33m',
    'DEBUG': '\033[94m',
}


class LoggerError(Exception):
    pass


class ColorFormatter(logging.Formatter):
    def format(self, record):
        s = super().format(record)
        if record.levelname in color_code:
            return '{}{}{}'.format(color_code[record.levelname], s, '\033[0m')
        return s


msg_fmt = '%(asctime)s - %(levelname)s: [%(name)s] %(message)s'
date_fmt = '%m.%d.%Y %I:%M:%S %p'
standard_formatter = logging.Formatter(fmt=msg_fmt, datefmt=date_fmt)
color_formatter = ColorFormatter(fmt=msg_fmt, datefmt=date_fmt)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(standard_formatter)

logger = logging.getLogger('connector')
logger.propagate = False
logger.addHandler(stream_handler)


def initLogging() -> None:
    if not cc_conf.logger.level in logging_levels.keys():
        err = "unknown log level '{}'".format(cc_conf.logger.level)
        raise LoggerError(err)
    if cc_conf.logger.colored:
        stream_handler.setFormatter(color_formatter)
    logger.setLevel(logging_levels[cc_conf.logger.level])
    if cc_conf.logger.rotating_log:
        logger.removeHandler(stream_handler)
        logs_path = '{}/logs'.format(user_dir)
        if not os.path.exists(logs_path):
            try:
                os.makedirs(logs_path)
            except OSError as ex:
                raise LoggerError(ex)
        file_path = '{}/connector.log'.format(logs_path)
        log_handler = logging.handlers.TimedRotatingFileHandler(
            file_path,
            when="midnight",
            backupCount=cc_conf.logger.rotating_log_backup_count
        )
        log_handler.setFormatter(standard_formatter)
        logger.addHandler(log_handler)


def getLogger(name: str) -> logging.Logger:
    return logger.getChild(name)
