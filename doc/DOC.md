# Message passing

The MISP instance is producing data that is send through ZMQ.

The script __zmq_subscriber.py__ tries to subscribe to it. Depending on the received message, it forwards the message to function that will handle it. Usually, these messages are parsed and useful functions in __*__\_helper might be called.

Real time data are sent to their respective server's Redis pubsub channel

![Message passing](./doc/message_passing.png "Message passing")

# Redis database

| Module              | Feature                               | Key name                       | Key type | Key content              |
|---------------------|---------------------------------------|--------------------------------|----------|--------------------------|
| Geolocalisation     | Coordinate per day                    | ```GEO_COORD:date```           | zset     |{lat: xx, lon: yy}        |
| Geolocalisation     | Country per day                       | ```GEO_COUNTRY:date```         | zset     |ISO_CODE                  |
| Geolocalisation     | Coordinate and value per radius       | ```GEO_RAD:date```             | geo      | { categ: xx, value: yy } |
| Contribution        | Contribution per day (monthly points) | ```CONTRIB_DAY:date```         | zset     | org                      |
| Contribution        | Category contributed per day          | ```CONTRIB_CATEG:date:categ``` | zset     | org                      |
| Contribution        | Last org that contributed             | ```CONTRIB_LAST:date```        | zset     | org                      |
| Contribution        | All org collected from the ZMQ        | ```CONTRIB_ALL_ORG```          | set      | org                      |
| Contribution        | Acquired contribution requirement     | ```CONTRIB_ORG:org:req```<br/> | string   | integer                  |
|                     | ```req``` is one of:                  | ```points``` <br/> ```CONTRIB_REQ_i``` <br/> ```ATTR_WEEK_COUNT``` <br/> ```PROP_WEEK_COUNT``` <br/> ```SIGHT_WEEK_COUNT``` <br/> ```EVENT_WEEK_COUNT``` <br/> ```EVENT_MONTH_COUNT``` <br/> ```BADGE_i``` <br/>                                                                                          |          |                          |
| Contribution        | Acquired trophy points                | ```CONTRIB_TROPHY:categ```     | zset     | org                      |
| Contribution        | Last org to get a trophy or badge     | ```CONTRIB_LAST_AWARDS:date``` | zset     | org                      |
