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


class ClientError(Exception):
    """
    Base error.
    """
    pass


class HubInitializationError(ClientError):
    """
    Error during hub initialization.
    """
    pass


class HubNotInitializedError(ClientError):
    """
    Hub has not been initialized.
    """
    pass


class HubNotFoundError(ClientError):
    """
    Hub ID not on platform.
    """
    pass


class HubSynchronizationError(ClientError):
    """
    Error during hub synchronization.
    """
    pass


class DeviceAddError(ClientError):
    """
    Error while adding a device.
    """
    pass


class DeviceNotFoundError(ClientError):
    """
    Device is missing.
    """
    pass


class DeviceDeleteError(ClientError):
    """
    Error while deleting a device.
    """
    pass


class DeviceConnectError(ClientError):
    """
    Error connecting a device.
    """
    pass


class DeviceDisconnectError(ClientError):
    """
    Error disconnecting a device.
    """
    pass


class DeviceUpdateError(ClientError):
    """
    Error while updating a device.
    """
    pass


class CommInitializedError(ClientError):
    """
    Communication has already been initialized.
    """
    pass


class CommNotInitializedError(ClientError):
    """
    Communication has not been initialized.
    """
    pass


class CommandQueueEmptyError(ClientError):
    """
    Command queue is empty.
    """
    pass


class SendError(ClientError):
    """
    Error sending a message.
    """
    pass


class SendResponseError(SendError):
    """
    Error sending a response.
    """
    pass


class SendEventError(SendError):
    """
    Error sending an event.
    """
    pass
