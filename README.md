connector-client
===================


A Python client providing a quasi-framework for users wanting to integrate their personal IoT project / device with the SEPL platform.

Written in Python3 and relying on the websockets module.


----------

**Environment variables:**

`CONNECTOR_LOOKUP_URL` (default: 'http://fgseitsrancher.wifa.intern.uni-leipzig.de:8093/lookup')

`CONNECTOR_DEVICE_REGISTRATION_PATH` (default: 'discovery')

`CONNECTOR_HTTPS` = (default: None)

`CONNECTOR_USER` = (default: '')

`CONNECTOR_PASSWORD` = (default: '')

`LOGLEVEL` = (default: 'info')

----------


Basic Example
-------------

```
try:
    from modules.logger import root_logger
    from modules.http_lib import Methods as http
    from connector.connector import Connector
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))

logger = root_logger.getChild(__name__)

# your code

if __name__ == '__main__':
    connector = Connector()
    # start your code
```

-------------
**Query parameters (optional):**

`time_window` limits the time-frame of the query. Accepts `h`, `m` and `s` as suffixes. (Example: `12h`)

`granularity` sets the granularity of the result. Available options: `all`, `second`, `minute`, `fifteen_minute`, `thirty_minute`, `hour`, `day`, `week`, `month`, `quarter`, `year`


**Returns a JSON array of JSON objects:**

`[{"time_stamp":<string>,"result":<float>,"data_points":<integer>}]`


**Example:**
```
GET /devices/your_device/average?granularity=hour&time_window=12h
```
Performs a "timeseries" query covering the last 12 hours and aggregates per hour:
```
-> [{"time_stamp":"2016-12-06T13:00:00.000Z","result":6.101150962541688,"data_points":53},{"time_stamp":"2016-11-29T12:00:00.000Z","result":6.0534987847972435,"data_points":1652}]
```
A simpler query:
```
GET /devices/your_device/average

-> [{"time_stamp":"2016-12-06T13:06:20.205Z","result":6.050372958501621,"data_points":10111}]
```
By omitting `granularity` the service uses `all` as a standard value and not providing `time_window` results in an interval ranging from the beginning of "Unix time" to the current time.
