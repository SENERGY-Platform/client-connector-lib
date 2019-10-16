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

__all__ = ('ActuatorService', 'SensorService', 'actuator_service', 'sensor_service')

from .._util import validateInstance, getSubclass


class Service:
    name = str()
    type = str()
    # input =
    # output =
    description = str()
    local_id = str()

    def __new__(cls, *args, **kwargs):
        if cls in (Service, ActuatorService, SensorService):
            __err = "instantiation of class '{}' not allowed".format(cls.__name__)
            raise TypeError(__err)
        return super(__class__, cls).__new__(cls)

    @classmethod
    def _validate(cls) -> None:
        for a_name, a_type in _getAttributes():
            attr = getattr(cls, a_name)
            validateInstance(attr, a_type)


class ActuatorService(Service):
    type = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Actuator"


class SensorService(Service):
    type = "http://www.sepl.wifa.uni-leipzig.de/ontlogies/device-repo#Sensor"


def actuator_service(obj) -> type:
    return getSubclass(obj, ActuatorService)


def sensor_service(obj) -> type:
    return getSubclass(obj, SensorService)


def _getAttributes() -> tuple:
    return tuple((name, type(obj)) for name, obj in Service.__dict__.items() if
                 not name.startswith("_") and not isinstance(obj, staticmethod) and name is not "type")
