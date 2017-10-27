# MISP-Dashboard
A Dashboard showing live data and statistics from the MISP ZMQ

## Installation
- Launch ```./install_dependencies.sh``` from the MISP-Dashboard directory
- Update the configuration file ```config.cfg``` so that it matches your system
  - Fields that you may change:
    - RedisGlobal -> host
    - RedisGlobal -> port
    - RedisLog -> zmq_url
    - RedisMap -> pathMaxMindDB

## Starting the System
- Activate your virtualenv ```. ./DASHENV/bin/activate```
- Listen to the MISP feed by starting the zmq_subscriber ```./zmq_subscriber.py```
- Start the Flask server ```./server.py```

## zmq_subscriber options
```usage: zmq_subscriber.py [-h] [-n ZMQNAME] [-u ZMQURL]

A zmq subscriber. It subscribe to a ZMQ then redispatch it to the MISP-dashboard

optional arguments:
  -h, --help            show this help message and exit
  -n ZMQNAME, --name ZMQNAME
                        The ZMQ feed name
  -u ZMQURL, --url ZMQURL
                        The URL to connect to
```
