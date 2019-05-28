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

__all__ = ('ActuatorService', 'SensorService', 'service')

from .._util import validateInstance
from inspect import stack, getmodule


class Type:
    pass


class Actuator(Type):
    uri = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Actuator"


class Sensor(Type):
    uri = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Sensor"


class Service:
    uri = str()
    name = str()
    type = str()
    # input =
    # output =
    description = str()


class ActuatorService(Service):
    type = Actuator

    def __new__(cls, *args, **kwargs):
        if cls is __class__:
            __err = "instantiation of class '{}' not allowed".format(__class__.__name__)
            raise TypeError(__err)
        return super(ActuatorService, cls).__new__(cls)


class SensorService(Service):
    type = Sensor

    def __new__(cls, *args, **kwargs):
        if cls is __class__:
            __err = "instantiation of class '{}' not allowed".format(__class__.__name__)
            raise TypeError(__err)
        return super(SensorService, cls).__new__(cls)


class service:
    __count = 0

    def __new__(cls, *args, **kwargs):
        __err = "instantiation of class '{}' not allowed".format(__class__.__name__)
        raise TypeError(__err)

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
        for a_name, a_type in __class__.__getAttributes():
            if isinstance(obj, dict):
                attr = obj[a_name]
            else:
                attr = getattr(obj, a_name)
            validateInstance(attr, a_type)

    @staticmethod
    def __getAttributes():
        return tuple((name, type(obj)) for name, obj in Service.__dict__.items() if
                     not name.startswith("_") and not isinstance(obj, staticmethod) and name is not "type")
