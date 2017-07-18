connector-client
================

A Python client providing a quasi-framework for users wanting to integrate their personal IoT project / device with the SEPL platform.

Written in Python3 and relying on the `websockets` module.

----------

> **Environment variables:**
> 
> `CONNECTOR_LOOKUP_URL` (default:
> 'http://fgseitsrancher.wifa.intern.uni-leipzig.de:8093/lookup')
> 
> `CONNECTOR_DEVICE_REGISTRATION_PATH` (default: 'discovery')
> 
> `CONNECTOR_HTTPS` (default: None)
> 
> `CONNECTOR_USER` (default: '')
> 
> `CONNECTOR_PASSWORD` (default: '')
> 
> `LOGLEVEL` (default: 'info')

----------

**Basic client structure**

    from modules.logger import root_logger
    from connector.connector import Connector
    from connector.message import Message
    from connector.device import Device
    
    logger = root_logger.getChild(__name__)
    
    
    # your code


    if __name__ == '__main__':
        connector = Connector()
        
        # start your code


-------------

Basic Usage
-----------

> **Send a message to the platform**
> 
>     Connector.send() 
> 
> Requires a `Message` object as argument.
> 
> ----------
> 
> **Receive a message from the platform**
> 
>     Connector.receive()
> 
> Blocks and returns when a message is received from the platform.
> Returned object is a `Message` object containing the payload and
> metadata.
> 
> ----------
> 
> **Register a device to the platform**
> 
>     Connector.register()
> 
> Requires a `Device` object as argument.
> 
>----------
>
> **Remove a device from the platform**
> 
>     Connector.unregister()
> 
> Requires a `Device` object as argument.

----------

Creating a device
-----------------

