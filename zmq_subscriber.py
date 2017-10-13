#!/usr/bin/env python3.5

import time
import zmq
import redis
import random
import configparser
import os
import sys
import json
import geoip2.database

configfile = os.path.join(os.environ['VIRTUAL_ENV'], '../config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

zmq_url = cfg.get('RedisLog', 'zmq_url')
zmq_url = "tcp://192.168.56.50:50000"
zmq_url = "tcp://localhost:9990"
channel = cfg.get('RedisLog', 'channel')
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(zmq_url)
socket.setsockopt_string(zmq.SUBSCRIBE, '')

redis_server = redis.StrictRedis(
        host=cfg.get('RedisLog', 'host'),
        port=cfg.getint('RedisLog', 'port'),
        db=cfg.getint('RedisLog', 'db'))
serv_coord = redis.StrictRedis(
        host='localhost',
        port=6250,
        db=1) 
path_to_db = "/home/sami/Downloads/GeoLite2-City_20171003/GeoLite2-City.mmdb"
reader = geoip2.database.Reader(path_to_db)

channel_proc = "CoordToProcess"
channel_disp = "PicToDisplay"


def publish_coord(coord):
    pass

def get_ip(data):
    pass

def ip_to_coord(ip):
    resp = reader.city(ip)
    lat = resp.location.latitude
    lon = resp.location.longitude
    return {'lat': lat, 'lon': lon}

def default_log(jsonevent):
    print('sending', 'log')
    return
    #redis_server.publish(channel, json.dumps(jsonevent))

def default_keepalive(jsonevent):
    print('sending', 'keepalive')
    to_push = [ jsonevent['uptime'] ]
    to_send = { 'name': 'Keepalive', 'log': json.dumps(to_push) }
    redis_server.publish(channel, json.dumps(to_send))

def default_event(jsonevent):
    print('sending', 'event')
    jsonevent = jsonevent['Event']
    to_push = [
            jsonevent['threat_level_id'],
            jsonevent['id'],
            jsonevent['info'],
            ]
    to_send = { 'name': 'Event', 'log': json.dumps(to_push) }
    redis_server.publish(channel, json.dumps(to_send))

def default_attribute(jsonevent):
    print('sending', 'attribute')
    jsonevent = jsonevent['Attribute']
    to_push = [
            jsonevent['id'],
            jsonevent['category'],
            jsonevent['type'],
            jsonevent['value'],
            ]

    #try to get coord
    if jsonevent['category'] == "Network activity":
        try:
            coord = ip_to_coord(jsonevent['value'])
            to_send = {'lat': float(coord['lat']), 'lon': float(coord['lon'])}
            serv_coord.publish(channel_proc, json.dumps(to_send))
            print('coord sent')
        except ValueError:
            print("can't resolve ip")

    to_send = { 'name': 'Attribute', 'log': json.dumps(to_push) }
    redis_server.publish(channel, json.dumps(to_send))


def process_log(event):
    event = event.decode('utf8')
    topic, eventdata = event.split(' ', maxsplit=1)
    jsonevent = json.loads(eventdata)
    dico_action[topic](jsonevent)


def main():
    while True:
        content = socket.recv()
        content.replace(b'\n', b'') # remove \n...
        process_log(content)

def log_feed():
    with open('misp-zmq.2', 'ba') as f:
    
        while True:
            time.sleep(1.0)
            content = socket.recv()
            content.replace(b'\n', b'') # remove \n...
            f.write(content)
            f.write(b'\n')
            print(content)
            #redis_server.publish(channel, content)
        
            #if random.randint(1,10)<5:
            #    time.sleep(0.5)
            #    redis_server.publish(channel, content)
        
            #if random.randint(1,10)<5:
            #    time.sleep(0.5)
            #    redis_server.publish(channel, content)

dico_action = {
        "misp_json":                default_event,
        "misp_json_self":           default_keepalive,
        "misp_json_attribute":      default_attribute,
        "misp_json_sighting":       default_log,
        "misp_json_organisation":   default_log,
        "misp_json_user":           default_log,
        "misp_json_conversation":   default_log
        }


if __name__ == "__main__":
    main()
    reader.close()



# server side
pubsub = redis_server.pubsub(ignore_subscribe_messages=True)

#while True:
#    rdm = random.randint(1,10)
#    time.sleep(float(rdm))
#    #lux
#    lon = random.uniform(5.7373, 6.4823)
#    lat = random.uniform(49.4061,49.7449)
#    #central eur
#    lon = random.uniform(3.936, 9.890)
#    lat = random.uniform(47.957, 50.999)
#    content = ["rdm "+str(rdm)]
#    content = [lat,lon]
#    jsonContent = json.dumps(content)
#    to_send = { 'name': 'feeder'+str(rdm), 'log': jsonContent }
#    redis_server.publish(channel, json.dumps(to_send))
#    serv_coord.publish(channel_proc, json.dumps({'lat': float(lat), 'lon': float(lon)}))


