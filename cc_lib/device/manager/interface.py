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

__all__ = ['Interface']

from abc import ABCMeta, abstractmethod


class Interface(metaclass=ABCMeta):
    """
    Interface class. Device managers must inherit from this class.
    """
    @abstractmethod
    def add(*sc, device):
        """
        add device
        :param device: takes a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def update(*sc, device):
        """
        update device
        :param device: takes a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def remove(*sc, id_str):
        """
        remove device
        :param id_str: takes device ID as string.
        """
        pass

    @abstractmethod
    def get(*sc, id_str):
        """
        get device
        :param id_str: takes device ID as string.
        :return a Device (or subclass of Device) object.
        """
        pass

    @abstractmethod
    def devices(*sc, _):
        """
        all devices
        :param _: don't use
        :return a dict, list or tuple object.
        """
        pass
