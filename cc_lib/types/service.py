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

__all__ = ('Service',)

from typing import Callable, Any


def Service(input=None, output=None):
    if any((type(input) is type, type(output) is type)):
        def wrap(func: Callable[[Any], Any]):
            def wrap_call(*args, **kwargs):
                return func(*args, **kwargs)
            setattr(wrap_call, "__service__", True)
            if input:
                setattr(
                    wrap_call,
                    "__input__",
                    {key: value for key, value in input.__dict__.items() if not key.startswith('_')}
                )
            else:
                setattr(wrap_call, "__input__", None)
            if output:
                setattr(
                    wrap_call,
                    "__output__",
                    {key: value for key, value in output.__dict__.items() if not key.startswith('_')}
                )
            else:
                setattr(wrap_call, "__output__", None)
            return wrap_call
    else:
        def wrap(*args, **kwargs):
            return input(*args, **kwargs)
        setattr(wrap, "__service__", True)
        setattr(wrap, "__input__", None)
        setattr(wrap, "__output__", None)
    return wrap