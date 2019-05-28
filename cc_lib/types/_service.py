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

__all__ = ('Service', )

from .._util import validateInstance
from inspect import stack, getmodule


class Type:
    pass


class Actuator(Type):
    uri = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Actuator"


class Sensor(Type):
    uri = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Sensor"


class BaseService:
    pass


class _Service(BaseService):
    pass


class Service(BaseService):
    uri = str()
    name = str()
    type = str()
    # input =
    # output =
    description = str()
    __count = 0

    def __new__(cls, *args, **kwargs):
        if cls is __class__:
            __err = "instantiation of class '{}' not allowed".format(__class__.__name__)
            raise TypeError(__err)
        return super(Service, cls).__new__(cls)

    @staticmethod
    def actuator(obj) -> type:
        sub_cls = __class__.__getSubclass(obj)
        setattr(sub_cls, "type", Actuator)
        return sub_cls

    @staticmethod
    def sensor(obj) -> type:
        sub_cls = __class__.__getSubclass(obj)
        setattr(sub_cls, "type", Sensor)
        return sub_cls

    @staticmethod
    def __getSubclass(obj):
        __class__.__validate(obj)
        if isinstance(obj, dict):
            sub_cls = type("{}_{}".format(Service.__name__, __class__.__count), (Service,), obj)
            __class__.__count += 1
            try:
                frm = stack()[-1]
                mod = getmodule(frm[0])
                setattr(sub_cls, "__module__", mod.__name__)
            except (IndexError, AttributeError):
                pass
            return sub_cls
        else:
            attr_dict = obj.__dict__.copy()
            del attr_dict['__dict__']
            del attr_dict['__weakref__']
            return type(obj.__name__, (Service,), attr_dict)

    @staticmethod
    def __validate(obj):
        validateInstance(obj, (type, dict))
        for a_name, a_type in __class__.__attributes:
            if isinstance(obj, dict):
                attr = obj[a_name]
            else:
                attr = getattr(obj, a_name)
            validateInstance(attr, a_type)
