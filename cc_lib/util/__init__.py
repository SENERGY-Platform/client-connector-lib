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


__all__ = ('Singleton', 'validateInstance', 'validateSubclass')


from typing import Any, Union, Tuple


class Singleton(type):
    """
    Subclass this class for singleton behavior
    """
    _instances = dict()
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def validateInstance(obj: object, cls: Union[type, Tuple[type, ...]]) -> None:
    if not isinstance(obj, cls):
        err = "{} not instance of {}".format(obj, cls)
        raise TypeError(err)


def validateSubclass(cls: type, parent_cls: Union[type, Tuple[type, ...]]) -> None:
    if not issubclass(cls, parent_cls):
        err = "{} not subclass of {}".format(cls, parent_cls)
        raise TypeError(err)


def getMangledAttr(obj: object, attr: str) -> Any:
    """
    Read mangled attribute.
    :param obj: Object with mangled attributes.
    :param attr: Name of mangled attribute.
    :return: value of mangled attribute.
    """
    return getattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr))


def setMangledAttr(obj: object, attr: str, arg: Any) -> None:
    """
    Write to mangled attribute.
    :param obj: Object with mangled attributes.
    :param attr: Name of mangled attribute.
    :param arg: value to be written.
    """
    setattr(obj, '_{}__{}'.format(obj.__class__.__name__, attr), arg)