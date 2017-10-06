connector-client
================

A Python client providing a quasi-framework for users wanting to integrate their personal IoT project / device with the SEPL platform.

Written in Python3 and relying on the `websockets` module.

----------


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
