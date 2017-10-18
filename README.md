connector-client
================

A Python client providing a quasi-framework for users wanting to integrate their personal IoT project / device with the SEPL platform.

Written in Python 3.4 and relying on the `websockets` module.

----------

**Configuration**

connector-client configuration is done via `connector.conf`

    [CONNECTOR]
    protocol = < ws / wss >
    host = < your-websocket-host.com / 123.128.12.45 >
    port = < websocket port >
    user = < sepl username >
    password = < sepl password >
    gid = < set by sepl platform >
    
    [LOGGER]
    level = < debug / info / warning / error / critical >
    rotating_log = < yes / no >
    rotating_log_backup_count = < number of backup copies to keep >

---

**Quick start**

    from connector.client import Client
    from connector.device import Device
    
    ## initiation phase ##
    
    # collect devices #
    for device in your_devices:
        your_device_manager.add(device)


    if __name__ == '__main__':
        connector_client = Client(device_manager=your_device_manager)
        
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


Support Modules
-----------------

**HTTP Library**

>     get(url)
> 
> >`url` requires a fully qualified URL string.   
> >
> >Optional:
> >
> >`query` takes a dictionary with query arguments.
> >
> >`headers` takes a dictionary with header fields.
> >
> >Returns a `Response` object.
> 
> ----------
> 
>      post(url, body)
> >`url` requires a fully qualified URL string. 
> >
> >`body` should be provided as a string.
> >
> >Optional:
> >
> >`headers` takes a dictionary with header fields.
> >
> >Returns a `Response` object.
> 
> ----------
> 
>      put(url, body)
> > `url` requires a fully qualified URL string. 
> >
> >`body` should be provided as a string.
> > 
> >
> > Optional:
> >
> > `headers` takes a dictionary with header fields.
> >
> > Returns a `Response` object.
> 
> ----------
> 
>       delete(url)
> > `url` requires a fully qualified URL string. 
> > 
> > Optional:
> >
> >`headers` takes a dictionary with header fields.
> >
> >Returns a `Response` object.
> 
> ----------
> 
>       header(url)
> > `url` requires a fully qualified URL string.
> > 
> > Optional:
> >
> > `query` takes a dictionary with query arguments.
> >
> > `headers` takes a dictionary with header fields.
> >
> > Returns a `Response` object.
> 
> ----------
> 
> **Global optional arguments**
> 
> `timeout` time to pass until a request fails in seconds. (default: 3)
> 
> `retries` number of retries for a failed request. (default: 0)
> 
> `retry_delay` delay between retries in seconds. (default: 0.5) 
> 
> ----------
> 
> **Response object structure**
> 
> `status` response status.
> 
> `header` response header.
> 
> `body` response body.
> 
> ----------
> 
> **Example**
>         
>     from modules.http_lib import Methods as http
>     
>     
>     # get http://www.yourdomain.com/path?id=1&lang=en
>     response = http.get(
>         'http://www.yourdomain.com/path',
>         query = {'id':1, 'lang':'en'}
>        )
>     body = response.body   
>     
>     response = http.post(
>         'http://www.yourdomain.com/path',
>         body = "{'unit': 'kW', 'value': '1.43'}",
>         headers = {'Content-Type': 'application/json'}
>        )
>     status = response.status


----------


**Logger**

> **Levels**
> 
>  `info`, `warning`, `error`, `critical` and `debug`
>  
>  ----------
> 
> **Example**
> 
>     from modules.logger import root_logger
>     
>     logger = root_logger.getChild(__name__)
>     
>     
>     logger.info('info message')
>     logger.warning('warning message')
>     logger.error('error message')
>     logger.critical('critical message')
>     logger.debug('debug message')
