"""
   Copyright 2018 InfAI (CC SES)

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

try:
    from connector_lib.modules.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json
from uuid import uuid4 as uuid


logger = root_logger.getChild(__name__)


class Message:
    """
    Class mapping the message (or envelope) structure used by the platform.
    """
    def __init__(self, handler=str()):
        """
        Create a Message object. Attributes must be set after instantiation.
        Users can only access 'status', 'content_type', 'payload'.
        :param handler: Optional handler. Use platform handlers map above.
        """
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

    def __repr__(self):
        """
        Provide a string representation.
        :return: String.
        """
        attributes = [
            ('status', self.status),
            ('content_type', self.content_type),
            ('payload', self.payload),
        ]
        return "{}({})".format(__class__.__name__, ", ".join(["=".join([key, str(value)]) for key, value in attributes]))


def getMangledAttr(obj, attr):
    """
    Read mangled attribute.
    :param obj: Object with mangled attributes.
    :param attr: Name of mangled attribute.
    :return: value of mangled attribute.
    """
    return getattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr))


def setMangledAttr(obj, attr, arg):
    """
    Write to mangled attribute.
    :param obj: Object with mangled attributes.
    :param attr: Name of mangled attribute.
    :param arg: value to be written.
    """
    setattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr), arg)


def marshalMsg(msg_obj: Message) -> str:
    """
    Marshal a Message object to JSON.
    :param msg_obj: Message object.
    :return: String.
    """
    return json.dumps({key.replace('_{}__'.format(msg_obj.__class__.__name__), ''): msg_obj.__dict__[key] for key in msg_obj.__dict__})


def unmarshalMsg(msg_str: str) -> Message:
    """
    Unmarshal JSON message.
    :param msg_str: JSON message as string.
    :return: Message object.
    """
    try:
        msg = json.loads(msg_str)
        msg_obj = Message()
        for key in msg:
            if msg[key]:
                setMangledAttr(msg_obj, key, msg[key])
        return msg_obj
    except Exception as ex:
        logger.error("malformed message: '{}'".format(msg_str))
        logger.debug(ex)
