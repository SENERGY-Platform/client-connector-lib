connector-client
================

Framework for users wanting to integrate their personal IoT project / device with the SEPL platform.

Written for Python >= 3.5.3 and relying on the `websockets` module.
For Python 3.4 please see legacy branch.

----------

+ [Quickstart](#quick-start)
+ [Configuration](#configuration)
+ [Client API](#client-api)
    + [Receive and respond](#receive-and-respond-to-a-task-command)
    + [Push event](#push-event)
    + [Add device](#add-device)
    + [Update device](#update-device)
    + [Disconnect device](#disconnect-device)
    + [Delete device](#delete-device)
    + [Asynchronous calls](#asynchronous-calls)
+ [Message Class](#message-class)
+ [Device Class](#device-class)
+ [Device Manger Interface](#device-manger-interface)
+ [Support Modules](#support-modules)
    + [In memory device management](#in-memory-device-management)
    + [Persistent device management](#persistent-device-management)
    + [HTTP Library](#http-library)
    + [Logger](#logger)
    + [Singleton Pattern](#singleton-pattern)
+ [Platform Specific Info](#platform-specific-info)

----------


##### Quick start

Start a connector-client by instantiating a `Client` object with a device manager object or class.

    class connector.client.Client(device_manager, con_callbck=None, discon_callbck=None)

> `device_manager` required (class or object), must implement `DeviceManagerInterface`
> 
> `con_callbck` callback after successful connection to SEPL platform
>
> `discon_callbck` callback on disconnect event
>
> **Important:** Provided callbacks must never block!

+ To avoid multiple instantiations the connector-client implements the singleton pattern.
+ The client API uses static methods, thus allowing calls directly from the class or an object. 
+ Threading is managed internally, wrapping the connector-client in a thread is not necessary.

Note the _'initiation phase'_ and _'runtime phase'_ in the example below. 
During initiation the user can collect available devices and store them in a device manager.
After all devices have been found the user can instantiate the connector-client and provide it with the collected devices.
The connector-client will try to connect to the SEPL platform and synchronise the provided devices.
Regardless of the success of the internal connection and synchronisation phase, the connector-client will return control to _'runtime phase'_.
During runtime users can execute their own code and make use of the client API.

    from connector.client import Client
    from connector.device import Device
    
    ## initiation phase ##
    
    # collect devices #
    for device in your_devices:
        your_device_manager.add(device)


    if __name__ == '__main__':
        connector_client = Client(your_device_manager)
        
        ## runtime phase ##

        # Receive command and respond #
        task = Client.receive()
        # do something
        Client.response(task, status)
        
        # Push event #
        Client.event(your_device, 'service', payload)
        
        # Register new device #
        new_device = Device('id', 'type', 'name')
        Client.register(new_device)
        
        # Update device #
        new_device.name = 'new name'
        Client.update(new_device)
        
        # Disconnect device #
        Client.disconnect('your_device_id')
        
        # Delete device #
        Client.delete(new_device)


##### Configuration

connector-client configuration is done via `connector/connector.conf`, if no conf file is found a new file will be generated.

    [CONNECTOR]
    encryption = < no / yes >
    host = < your-websocket-host.com / 123.128.12.45 >
    port = < websocket port >
    user = < sepl username >
    password = < sepl password >
    gid = < set by sepl platform >
    
    [LOGGER]
    level = < debug / info / warning / error / critical >
    rotating_log = < yes / no >
    rotating_log_backup_count = < number of backup copies to keep >


Client API
-----------------

##### Receive and respond to a task / command

    Client.receive()
Blocks until a task / command is received from the platform. Returns a `Message` object containing a payload and metadata.

    Client.response(msg_obj, data, metadata=None, timeout=10, callback=None, block=True)
Requires a `Message` object returned by `Client.receive()` and data concerning the execution of the task / command.

---

##### Push event

    Client.event(device, service, data, metadata=None, timeout=10, callback=None, block=True)

Requires a device ID (or `Device` object), sepl-service and event data.

Returns a response `Message`.

---

##### Add device

    Client.add(device, timeout=10, callback=None, block=True)
    
Adds a device to the connector-client via the provided device manager and if possible registers the device with the platform.

Requires a `Device` object.

Returns true only on successful device registration. Devices will always be added to the device manager, regardless of registration success.

---

##### Update device

    Client.update(device, timeout=10, callback=None, block=True)
    
Updates a existing Device on the connector-client and if possible publishes the changes to the platform.

Requires a `Device` object.

Returns true only on successful publish. Devices will always be updated internally (device manager), regardless of publish success.

---

##### Disconnect device

    Client.disconnect(device, timeout=10, callback=None, block=True)

Deletes a device from the connector-client and if possible disconnects it from the platform. Disconnecting a device allows for devices to be retained on the platform (in a disconnected state) and thus remain available for further user actions.

Requires a device ID (or `Device` object).

Returns true only on successful disconnect. Devices will always be deleted internally (device manager), regardless of disconnect success.

---

##### Delete device

    Client.delete(device, timeout=10, callback=None, block=True)

Deletes a device from the connector-client and if possible deletes it from the platform. If deleting a device from the platform isn't possible, the device will enter a disconnected state after a successful connector-client reconnect and further user action is required.

Requires a device ID (or `Device` object).

Returns true only on successful delete. Devices will always be deleted internally (device manager), regardless of delete success.

---

##### Asynchronous calls

All methods block by default with a 10s timeout. If asynchronous behaviour is desired set `block=False` and if required provide a callback method to retrieve results. Asynchronous calls honor the timeout argument and provide a result upon timeout.

Callbacks should conform to the following signature with a reserved leading positional argument:

    def your_callback(msg_obj, *your_args, **your_kwargs):
        # your code

   
Message Class
-----------------
Used for communication between connector-client and sepl platform.

**Important:**
Users are not required to instantiate `Message` objects, they are obtained via the methods described in the 'Client API' section above.

**Attributes**

+ `status` HTTP status codes (set by platform)
+ `content_type` type of the data contained in payload (set by platform)
+ `payload` contains data


Device Class
-----------------
Provides a standard structure for Users to map device attributes and manage device tags.

    class connector.device.Device(id, type, name)

> Requires device ID, type and name.

Users requiring more advanced structures / behavior can subclass this class but must not forget to call `super().__init__(id, type, name)` during instantiation.

**Attributes**

+ `id` local device ID
+ `type` device type _(must be defined beforehand via platform)_
+ `name` device name
+ `tags` device tags
+ `hash` SHA1 hash calculated from above attributes

**Methods**

    addTag(tag_id, tag)

> Create new tag.

    changeTag(tag_id, tag)

> Change existing tag.

    removeTag(tag_id)

> Remove existing tag.


Device Manger Interface
-----------------

Users wanting to implement their own device manager must use the provided interface `DeviceManagerInterface`.

    from connector.device import DeviceManagerInterface
    
    class YourDeviceManager(DeviceManagerInterface):
        # your code

**Required methods**

Required methods can be normal, class or static methods.

    def add(device):
        # your code
  
Add a device to the device manager. Requires a `Device` (or subclass of `Device`) object.

    def update(device):
        # your code

Update existing device. Requires a `Device` (or subclass of `Device`) object.

    def remove(id_str):
        # your code
        
Remove device from device manager. Requires device ID as string.

    def get(id_str):
        # your code

Get a device from the device manager. Requires device ID as string and return a `Device` (or subclass of `Device`) object.

    def devices():
        # your code

Retrieve all devices from the device manager. Return a `dict` _(id:device)_, `list` or `tuple` containing `Device` (or subclass of `Device`) objects.


Support Modules
-----------------

##### In memory device management

Device manager storing and managing devices via a `dict` in memory. Uses static methods, no instantiation required.

    from modules.device_pool import DevicePool
    
    for device in your_devices:
        DevicePool.add(device)
    
    if __name__ == '__main__':
        connector_client = Client(device_manager=DevicePool)
     

---

##### Persistent device management

Device manager storing and managing devices in a sqlite database (Singleton instance). 
Only supports `Device` objects.

    from modules.device_pool import DeviceStore
    
    device_manager = DeviceStore()
    
    for device in your_devices:
        device_manager.add(device)
    
    if __name__ == '__main__':
        connector_client = Client(device_manager=device_manager)
     
---

##### HTTP Library

    get(url, query=None, headers=None, auth=None, timeout=3, retries=0, retry_delay=0.5)
 
> `url` requires a fully qualified URL string.   
>
> `query` takes a dictionary with query arguments.
> 
> `headers` takes a dictionary with header fields.
>
> `auth` takes (username, password) tuple.


     post(url, body, headers=None, auth=None, timeout=3, retries=0, retry_delay=0.5)

> `url` requires a fully qualified URL string. 
>
> `body` should be provided as a string.
>
> `headers` takes a dictionary with header fields.
>
> `auth` takes (username, password) tuple.


     put(url, body, headers=None, auth=None, timeout=3, retries=0, retry_delay=0.5)

> `url` requires a fully qualified URL string. 
> 
> `body` should be provided as a string.
> 
> `headers` takes a dictionary with header fields.
>
> `auth` takes (username, password) tuple.


      delete(url, headers=None, auth=None, timeout=3, retries=0, retry_delay=0.5)

> `url` requires a fully qualified URL string. 
>  
> `headers` takes a dictionary with header fields.
>
> `auth` takes (username, password) tuple.


      header(url, query=None, headers=None, auth=None, timeout=3, retries=0, retry_delay=0.5)

> `url` requires a fully qualified URL string.
> 
> `query` takes a dictionary with query arguments.
>
> `headers` takes a dictionary with header fields.
>
> `auth` takes (username, password) tuple.


**Response object returned by above methods**

`status` response status.

`header` response header.

`body` response body.


    from modules.http_lib import Methods as http
    
    # get http://www.yourdomain.com/path?id=1&lang=en
    response = http.get(
        'http://www.yourdomain.com/path',
        query = {'id':1, 'lang':'en'}
       )
    body = response.body   
    
    response = http.post(
        'http://www.yourdomain.com/path',
        body = "{'unit': 'kW', 'value': '1.43'}",
        headers = {'Content-Type': 'application/json'}
       )
    status = response.status


----------


##### Logger

If user logs ought to be combined with connector-client logs, please create your own logger and use the `connector_client_log_handler`.


    from modules.logger import connector_client_log_handler
    import logging
    
    logger = logging.getLogger(__name__) # set desired logger name
    logger.setLevel(logging.DEBUG) # set desired logging level
    logger.addHandler(connector_client_log_handler)
    
    logger.debug('debug message')   
    logger.info('info message')
    logger.warning('warning message')
    logger.error('error message')
    logger.critical('critical message')


---------


##### Singleton Pattern


If the instantiation of a class is to be restricted to only one object this module provides two classes that can be subclassed by the user.

Use `Singleton` for most cases:

    from modules.singleton import Singleton
    
    YourClass(Singleton):
        # your code

Use `SimpleSingleton` if your class inherits from abstract classes:

    from modules.singleton import SimpleSingleton
    
    YourClass(DeviceManagerInterface, SimpleSingleton):
        # your code


Platform Specific Info
-----------------

The connector-client uses the `standard-connector` protocol.
Please be sure to select the right protocol when creating new device types.

The `standard-connector` protocol consists of:

+ `metadata`
+ `data`

A _'command / task'_ payload received from the SEPL platform will have the following structure:

    [
        {
            'name': 'metadata',
            'value': < ... >
        },
        {
            'name': 'data',
            'value': < ... >
        }
    ]

Users can currently access the above data via the key `protocol_parts`:

    msg_obj = Client.receive()
    command = msg_obj.payload.get('protocol_parts')
    
For further information see test `9` in `test_client.py` and the [connector](https://gitlab.wifa.uni-leipzig.de/fg-seits/connector) project.