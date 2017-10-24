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
channel = cfg.get('RedisLog', 'channel')
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(zmq_url)
socket.setsockopt_string(zmq.SUBSCRIBE, '')
channelDisp = cfg.get('RedisMap', 'channelDisp')

redis_server = redis.StrictRedis(
        host=cfg.get('RedisLog', 'host'),
        port=cfg.getint('RedisLog', 'port'),
        db=cfg.getint('RedisLog', 'db'))
serv_coord = redis.StrictRedis(
        host=cfg.get('RedisMap', 'host'),
        port=cfg.getint('RedisMap', 'port'),
        db=cfg.getint('RedisMap', 'db'))
path_to_db = "/home/sami/Downloads/GeoLite2-City_20171003/GeoLite2-City.mmdb"
reader = geoip2.database.Reader(path_to_db)

channel_proc = "CoordToProcess"

def publish_log(name, content):
    to_send = { 'name': name, 'log': json.dumps(content) }
    redis_server.publish(channel, json.dumps(to_send))


def ip_to_coord(ip):
    resp = reader.city(ip)
    lat = float(resp.location.latitude)
    lon = float(resp.location.longitude)
    # 0.0001 correspond to ~10m
    # Cast the float so that it has the correct float format
    lat_corrected = float("{:.4f}".format(lat))
    lon_corrected = float("{:.4f}".format(lon))
    return { 'coord': {'lat': lat_corrected, 'lon': lon_corrected}, 'full_rep': resp }

def getCoordAndPublish(supposed_ip, categ):
    try:
        rep = ip_to_coord(supposed_ip)
        coord = rep['coord']
        coord_dic = {'lat': coord['lat'], 'lon': coord['lon']}
        coord_list = [coord['lat'], coord['lon']]
        now = datetime.datetime.now()
        today_str = str(now.year)+str(now.month)+str(now.day)
        keyname = 'GEO_' + today_str
        serv_coord.zincrby(keyname, coord_list)
        to_send = {
                "coord": coord,
                "categ": categ,
                "value": supposed_ip,
                "country": rep['full_rep'].country.name,
                "specifName": rep['full_rep'].subdivisions.most_specific.name,
                "cityName": rep['full_rep'].city.name,
                "regionCode": rep['full_rep'].country.iso_code,
                }
        serv_coord.publish(channelDisp, json.dumps(to_send))
    except ValueError:
        print("can't resolve ip")

##############
## HANDLERS ##
##############

def handler_log(jsonevent):
    print('sending', 'log')
    return

def handler_keepalive(jsonevent):
    print('sending', 'keepalive')
    to_push = [ jsonevent['uptime'] ]
    publish_log('Keepalive', to_push)

def handler_event(jsonevent):
    print(jsonevent)
    #fields: threat_level_id, id, info
    jsonevent = jsonevent['Event']
    #redirect to handler_attribute
    if 'Attribute' in jsonevent:
        attributes = jsonevent['Attribute']
        if attributes is list:
            for attr in attributes:
                handler_attribute(attr)
        else:
            handler_attribute(jsonevent)


def handler_attribute(jsonattr):
    print(jsonattr)
    jsonattr = jsonattr['Attribute']
    to_push = []
    for field in json.loads(cfg.get('Log', 'fieldname_order')):
        if type(field) is list:
            to_add = cfg.get('Log', 'char_separator').join([ jsonattr[subField] for subField in field ])
        else:
            to_add = jsonattr[field]
        to_push.append(to_add)

    #try to get coord
    if jsonattr['category'] == "Network activity":
        getCoordAndPublish(jsonattr['value'], jsonattr['category'])

    publish_log('Attribute', to_push)


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


dico_action = {
        "misp_json":                handler_event,
        "misp_json_self":           handler_keepalive,
        "misp_json_attribute":      handler_attribute,
        "misp_json_sighting":       handler_log,
        "misp_json_organisation":   handler_log,
        "misp_json_user":           handler_log,
        "misp_json_conversation":   handler_log
        }


if __name__ == "__main__":
    main()
    reader.close()

