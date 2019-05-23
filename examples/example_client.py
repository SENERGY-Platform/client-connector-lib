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

import cc_lib, time, json, logging

logger = cc_lib.logger.getLogger(__name__)
logger.setLevel(logging.DEBUG)


scenario = {
    1: [0, 1, 2, 3, 4],
    2: [0, 5, 6],
    3: [0, 7, 8],
    4: [0, 9],
    5: [0, 10, 11, 12, 13, 14],
    6: []
}

tests = scenario[6]


device_manager = cc_lib.types.manager.DevicePool

client_connector = cc_lib.client.Client(device_manager)


logger.info('###### initiation phase ######')

id_1 = 'asdsdfsf24t'
id_2 = '3g46h4h6h436h'
id_3 = '46j5j67j6rt'
id_4 = '3h6j6i8i7rer5'


if 0 in tests:
    logger.info('------ populate device manager ------')
    device_manager.add(cc_lib.types.Device(id_1, 'iot#d66ec9bc-e37f-4f35-a788-027301aad6c2', 'Dummy Device 1'))
    device_2 = cc_lib.types.Device(id_2, 'iot#d66ec9bc-e37f-4f35-a788-027301aad6c2', 'Dummy Device 2')
    device_2.addTag('type', 'Dummy')
    device_manager.add(device_2)
    device_manager.add(cc_lib.types.Device(id_3, 'iot#d66ec9bc-e37f-4f35-a788-027301aad6c2', 'Dummy Device 3'))


if __name__ == '__main__':
    client_connector.begin()

    logger.info('###### runtime phase ######')

    if 1 in tests:
        time.sleep(0.5)
        logger.info('------ add tag to existing device ------')
        device = device_manager.get(id_1)
        device.addTag('type', 'Dummy')
        client_connector.update(device)

    if 2 in tests:
        time.sleep(0.5)
        logger.info('------ change tag on existing device ------')
        device = device_manager.get(id_1)
        device.changeTag('type', 'dummy device')
        client_connector.update(device)

    if 3 in tests:
        time.sleep(0.5)
        logger.info('------ remove tag on existing device ------')
        device = device_manager.get(id_2)
        device.removeTag('type')
        client_connector.update(device)

    if 4 in tests:
        time.sleep(0.5)
        logger.info('------ change name of existing device ------')
        device = device_manager.get(id_3)
        device.name = 'Dummy Smart Bulb'
        client_connector.update(device)

    if 5 in tests:
        time.sleep(0.5)
        logger.info('------ disconnect existing device ------')
        client_connector.disconnect(id_1)

    if 6 in tests:
        time.sleep(0.5)
        logger.info('------ delete existing device ------')
        client_connector.delete(id_3)

    if 7 in tests:
        time.sleep(0.5)
        logger.info('------ add new device ------')
        new_device = cc_lib.types.Device(id_4, 'iot#1740e97f-1ae1-4547-a757-a62018083d3f', 'Dummy Device 4')
        client_connector.add(new_device)

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
            response = client_connector.event(id_4, 'dummy-event', data, 'dummy metadata {}'.format(event))
            logger.info("event response '{}'".format(response.payload))

    if 9 in tests:
        time.sleep(0.5)
        logger.info('------ receive command and respond ------')
        msg_obj = client_connector.receive()
        device_id = msg_obj.payload.get('device_url')
        service = msg_obj.payload.get('service_url')
        command = msg_obj.payload.get('protocol_parts')
        logger.info("received command for device '{}' on service '{}':".format(device_id, service))
        logger.info(command)
        client_connector.response(msg_obj, '200', 'status')
        logger.info('sent response')

    if 10 in tests:
        time.sleep(0.5)
        logger.info('------ add existing device ------')
        new_device = cc_lib.types.Device(id_1, 'iot#1740e97f-1ae1-4547-a757-a62018083d3f', 'Dummy Device 1')
        client_connector.add(new_device)

    if 11 in tests:
        time.sleep(0.5)
        logger.info('------ disconnect unknown device ------')
        client_connector.disconnect('0okm9ijn')

    if 12 in tests:
        time.sleep(0.5)
        logger.info('------ delete unknown device ------')
        client_connector.delete('mko0nji9')

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
