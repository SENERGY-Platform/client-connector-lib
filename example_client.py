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
    from connector_client.modules.logger import connector_client_log_handler
    from connector_client.client import Client
    from connector_client.device import Device
    from connector_client.modules.device_pool import DevicePool
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time, json, logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(connector_client_log_handler)


scenario = {
    1: [0, 1, 2, 3, 4],
    2: [0, 5, 6],
    3: [0, 7, 8],
    4: [0, 9],
    5: [0, 10, 11, 12, 13, 14],
    6: []
}

tests = scenario[6]


logger.info('###### initiation phase ######')

id_1 = 'asdsdfsf24t'
id_2 = '3g46h4h6h436h'
id_3 = '46j5j67j6rt'
id_4 = '3h6j6i8i7rer5'

device_manager = DevicePool

if 0 in tests:
    logger.info('------ populate device manager ------')
    device_manager.add(Device(id_1, 'iot#d66ec9bc-e37f-4f35-a788-027301aad6c2', 'Dummy Device 1'))
    device_2 = Device(id_2, 'iot#d66ec9bc-e37f-4f35-a788-027301aad6c2', 'Dummy Device 2')
    device_2.addTag('type', 'Dummy')
    device_manager.add(device_2)
    device_manager.add(Device(id_3, 'iot#d66ec9bc-e37f-4f35-a788-027301aad6c2', 'Dummy Device 3'))


if __name__ == '__main__':
    connector_client = Client(device_manager)

    logger.info('###### runtime phase ######')

    if 1 in tests:
        time.sleep(0.5)
        logger.info('------ add tag to existing device ------')
        device = device_manager.get(id_1)
        device.addTag('type', 'Dummy')
        Client.update(device)

    if 2 in tests:
        time.sleep(0.5)
        logger.info('------ change tag on existing device ------')
        device = device_manager.get(id_1)
        device.changeTag('type', 'dummy device')
        Client.update(device)

    if 3 in tests:
        time.sleep(0.5)
        logger.info('------ remove tag on existing device ------')
        device = device_manager.get(id_2)
        device.removeTag('type')
        Client.update(device)

    if 4 in tests:
        time.sleep(0.5)
        logger.info('------ change name of existing device ------')
        device = device_manager.get(id_3)
        device.name = 'Dummy Smart Bulb'
        Client.update(device)

    if 5 in tests:
        time.sleep(0.5)
        logger.info('------ disconnect existing device ------')
        Client.disconnect(id_1)

    if 6 in tests:
        time.sleep(0.5)
        logger.info('------ delete existing device ------')
        Client.delete(id_3)

    if 7 in tests:
        time.sleep(0.5)
        logger.info('------ add new device ------')
        new_device = Device(id_4, 'iot#1740e97f-1ae1-4547-a757-a62018083d3f', 'Dummy Device 4')
        Client.add(new_device)

    if 8 in tests:
        time.sleep(0.5)
        logger.info('------ push 5 events ------')
        for event in range(5):
            data = json.dumps(
                {
                    'str_field': 'dummy event',
                    'int_field': event
                }
            )
            response = Client.event(id_4, 'dummy-event', data, 'dummy metadata {}'.format(event))
            logger.info("event response '{}'".format(response.payload))

    if 9 in tests:
        time.sleep(0.5)
        logger.info('------ receive command and respond ------')
        msg_obj = Client.receive()
        device_id = msg_obj.payload.get('device_url')
        service = msg_obj.payload.get('service_url')
        command = msg_obj.payload.get('protocol_parts')
        logger.info("received command for device '{}' on service '{}':".format(device_id, service))
        logger.info(command)
        Client.response(msg_obj, '200', 'status')
        logger.info('sent response')

    if 10 in tests:
        time.sleep(0.5)
        logger.info('------ add existing device ------')
        new_device = Device(id_1, 'iot#1740e97f-1ae1-4547-a757-a62018083d3f', 'Dummy Device 1')
        Client.add(new_device)

    if 11 in tests:
        time.sleep(0.5)
        logger.info('------ disconnect unknown device ------')
        Client.disconnect('0okm9ijn')

    if 12 in tests:
        time.sleep(0.5)
        logger.info('------ delete unknown device ------')
        Client.delete('mko0nji9')

    if 13 in tests:
        time.sleep(0.5)
        logger.info('------ remove unknown tag on existing device ------')
        device = device_manager.get(id_1)
        device.removeTag('type')

    if 14 in tests:
        time.sleep(0.5)
        logger.info('------ change unknown tag on existing device ------')
        device = device_manager.get(id_1)
        device.changeTag('type', 'Dummy')
