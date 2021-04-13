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

__all__ = ('Service', 'service')

from .._util import validate_instance, get_subclass


class Service:
    local_id = str()

    def __new__(cls, *args, **kwargs):
        if cls is __class__:
            __err = "instantiation of class '{}' not allowed".format(cls.__name__)
            raise TypeError(__err)
        return super(__class__, cls).__new__(cls)


def service(obj: type) -> type:
    validate_instance(obj, type)
    return get_subclass(obj, Service)
