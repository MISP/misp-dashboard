# Message passing

The MISP instance is producing data that is send through ZMQ.

The script __zmq_subscriber.py__ tries to subscribe to it. Depending on the received message, it forwards the message to function that will handle it. Usually, these messages are parsed and useful functions in __*__\_helper might be called.

Real time data are sent to their respective server's Redis pubsub channel

![Message passing](./doc/message_passing.png "Message passing")

# Redis database

## Geolocalisation

| Module              | Feature                               | Key name                           | Key type | Key content              |
|---------------------|---------------------------------------|------------------------------------|----------|--------------------------|
| geo_helper          | Coordinate per day                    | ```GEO_COORD:date```               | zset     |{lat: xx, lon: yy}        |
| geo_helper          | Country per day                       | ```GEO_COUNTRY:date```             | zset     |ISO_CODE                  |
| geo_helper          | Coordinate and value per radius       | ```GEO_RAD:date```                 | geo      | { categ: xx, value: yy } |

## Contribution

| Module              | Feature                               | Key name                           | Key type | Key content              |
|---------------------|---------------------------------------|------------------------------------|----------|--------------------------|
| contributor_helper  | Contribution per day (monthly points) | ```CONTRIB_DAY:date```             | zset     | org                      |
| contributor_helper  | Category contributed per day          | ```CONTRIB_CATEG:date:categ```     | zset     | org                      |
| contributor_helper  | Last org that contributed             | ```CONTRIB_LAST:date```            | zset     | org                      |
| contributor_helper  | All org collected from the ZMQ        | ```CONTRIB_ALL_ORG```              | set      | org                      |
| contributor_helper  | Acquired contribution requirement     | ```CONTRIB_ORG:org:req```<br/>     | string   | integer                  |
|                     | ```req``` is one of:                  | ```points``` <br/> ```CONTRIB_REQ_i``` <br/> ```ATTR_WEEK_COUNT``` <br/> ```PROP_WEEK_COUNT``` <br/> ```SIGHT_WEEK_COUNT``` <br/> ```EVENT_WEEK_COUNT``` <br/> ```EVENT_MONTH_COUNT``` <br/> ```BADGE_i``` <br/>                                                                                              |          | with TTL set accordingly |
| contributor_helper  | Acquired trophy points                | ```CONTRIB_TROPHY:categ```         | zset     | org                      |
| contributor_helper  | Last org to get a trophy or badge     | ```CONTRIB_LAST_AWARDS:date```     | zset     | org                      |

## Users

| Module              | Feature                               | Key name                           | Key type | Key content              |
|---------------------|---------------------------------------|------------------------------------|----------|--------------------------|
| users_helper        | Use to consider only one org per hour | ```LOGIN_TIMESTAMPSET:date_hour``` | set      | org (TTL = 1 hour)       |
| users_helper        | Use to get when users connect to MISP | ```LOGIN_TIMESTAMP:date```         | set      | timestamp                |
| users_helper        | When an org connects to MISP          | ```LOGIN_ORG:date```               | zset     | org                      |

## Trendings
| Module              | Feature                               | Key name                           | Key type | Key content              |
|---------------------|---------------------------------------|------------------------------------|----------|--------------------------|
| trendings_helper    | Popularity of type                    | ```TRENDINGS_type:date```          | zset     | type_name                |
|                     | ```type``` is one of:                 | ```EVENTS``` <br/> ```CATEGS``` <br/> ```TAGS``` <br/> ```DISC``` <br/>                                                                                              |          |                          |
| trendings_helper    | Popularity of type                    | ```TRENDINGS_SIGHT_type:date```    | string   | integer                  |
|                     | ```type``` is one of:                 | ```sightings``` <br/> ```false_positive```|   |                          ||
