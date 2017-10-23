#!/usr/bin/env python3.5

import time, datetime
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
    lat = float(resp.location.latitude)
    lon = float(resp.location.longitude)
    # 0.0001 correspond to ~10m
    # Cast the float so that it has the correct float format
    lat_corrected = float("{:.4f}".format(lat))
    lon_corrected = float("{:.4f}".format(lon))
    return {'lat': lat_corrected, 'lon': lon_corrected}

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

def default_attribute(jsonattr):
    print('sending', 'attribute')
    jsonattr = jsonattr['Attribute']
    to_push = [
            jsonattr['id'],
            jsonattr['category'],
            jsonattr['type'],
            jsonattr['value'],
            ]

    #try to get coord
    if jsonattr['category'] == "Network activity":
        handleCoord(jsonattr['value'], jsonattr['category'])

    to_send = { 'name': 'Attribute', 'log': json.dumps(to_push) }
    redis_server.publish(channel, json.dumps(to_send))

def handleCoord(supposed_ip, categ):
    try:
        coord = ip_to_coord(supposed_ip)
        coord_dic = {'lat': coord['lat'], 'lon': coord['lon']}
        coord_list = [coord['lat'], coord['lon']]
        print(coord_list)
        now = datetime.datetime.now()
        today_str = str(now.year)+str(now.month)+str(now.day)
        keyname = 'GEO_' + today_str
        serv_coord.zincrby(keyname, coord_list)
        to_send = {
                "coord": coord,
                "categ": categ,
                "value": supposed_ip
                }
        serv_coord.publish(channel_disp, json.dumps(to_send))
    except ValueError:
        print("can't resolve ip")

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

