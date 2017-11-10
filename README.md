# MISP-Dashboard
An experimental Dashboard showing live data and statistics from the MISP ZMQ

## Installation
- Launch ```./install_dependencies.sh``` from the MISP-Dashboard directory
- Update the configuration file ```config.cfg``` so that it matches your system
  - Fields that you may change:
    - RedisGlobal -> host
    - RedisGlobal -> port
    - RedisGlobal -> zmq_url
    - RedisGlobal -> misp_web_url
    
## Starting the System
- Activate your virtualenv ```. ./DASHENV/bin/activate```
- Listen to the MISP feed by starting the zmq_subscriber ```./zmq_subscriber.py```
- Start the Flask server ```./server.py```
- Access the interface at ```http://localhost:8001/```

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

## Screenshots

### Live Dashboard
![MISP event view](./screenshots/dashboard-live.png)

### Geo Dashboard
![MISP event view](./screenshots/dashboard-geo.png)

### Contributors Dashboard
![Dashboard-contributor2](./screenshots/dashboard-contributors2.png)
![Dashboard-contributor3](./screenshots/dashboard-contributors3.png)

## License
Images and logos are handmade for:
- rankingMISPOrg/
- rankingMISPMonthly/
- MISPHonorableIcons/

Note that:
- Part of ```MISPHonorableIcons/1.svg``` comes from [octicons.github.com](https://octicons.github.com/icon/git-pull-request/) (CC0 - No Rights Reserved)
- Part of ```MISPHonorableIcons/2.svg``` comes from [Zeptozephyr](https://zeptozephyr.deviantart.com/art/Vectored-Portal-Icons-207347804) (CC0 - No Rights Reserved)

```
Copyright (C) 2017 CIRCL - Computer Incident Response Center Luxembourg (c/o smile, security made in Lëtzebuerg, Groupement d'Intérêt Economique)
Copyright (c) 2017 Sami Mokaddem


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```
