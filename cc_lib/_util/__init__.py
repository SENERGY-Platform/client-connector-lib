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


__all__ = (
    'validate_instance',
    'validate_subclass',
    'calc_nth_term',
    'calc_duration',
    'getSubclass'
)

import typing
import inspect
import math
import uuid


def validate_instance(obj: object, cls: typing.Union[type, typing.Tuple[type, ...]]) -> None:
    """
    Raise TypeError if given object is not an instance of given class.
    Also works with instances of sub classes derived from the given class.
    :param obj: Object to be validated.
    :param cls: Class to check against.
    :return: None.
    """
    if not isinstance(obj, cls):
        err = "instance of {} required but got {}".format(cls, type(obj))
        raise TypeError(err)


def validate_subclass(cls: type, parent_cls: typing.Union[type, typing.Tuple[type, ...]]) -> None:
    """
    Raise TypeError if given class is not sub class of given class.
    :param cls: Class to be validated.
    :param parent_cls: Class to check against.
    :return: None.
    """
    if not issubclass(cls, parent_cls):
        err = "{} not subclass of {}".format(cls, parent_cls)
        raise TypeError(err)


def calc_nth_term(a_1: typing.Union[float, int], r: typing.Union[float, int], n: typing.Union[float, int]) -> typing.Union[float, int]:
    """
    Calculates the nth term of a geometric progression (an = a1 * r^(n-1)).
    :param a_1: First term.
    :param r: Common ratio.
    :param n: Number of desired term.
    :return: Float or integer.
    """
    return a_1 * r ** (n - 1)


def calc_duration(min_duration: int, max_duration: int, retry_num: int, factor: typing.Union[float, int]) -> int:
    """
    Calculate a value to be used as sleep duration based on a geometric progression.
    Won't return values above max_duration.
    :param min_duration: Minimum value to be returned.
    :param max_duration: Maximum value to be returned.
    :param retry_num: Number iterated by a loop calling the method.
    :param factor: Speed at which the maximum value will be reached.
    :return: Integer.
    """
    try:
        base_value = calc_nth_term(min_duration, factor, retry_num)
        magnitude = int(math.log10(math.ceil(base_value)))+1
        duration = math.ceil(base_value / 10 ** (magnitude - 1)) * 10 ** (magnitude - 1)
        if duration <= max_duration:
            return duration
    except OverflowError:
        pass
    return max_duration


def getSubclass(obj: typing.Union[type, dict], parent: type):
    validate_instance(obj, (type, dict))
    if isinstance(obj, dict):
        sub_cls = type("{}_{}".format(parent.__name__, uuid.uuid4().hex), (parent,), obj)
        try:
            frm = inspect.stack()[-1]
            mod = inspect.getmodule(frm[0])
            setattr(sub_cls, "__module__", mod.__name__)
        except (IndexError, AttributeError):
            pass
        return sub_cls
    else:
        attr_dict = obj.__dict__.copy()
        del attr_dict['__dict__']
        del attr_dict['__weakref__']
        return type(obj.__name__, (parent,), attr_dict)
