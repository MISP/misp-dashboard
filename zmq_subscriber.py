#!/usr/bin/env python3.5

import time
import zmq
import redis
import random
import configparser
import os
import sys
import json

configfile = os.path.join(os.environ['VIRTUAL_ENV'], '../config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

zmq_url = cfg.get('RedisLog', 'zmq_url')
zmq_url = "tcp://crf.circl.lu:5556"
channel = cfg.get('RedisLog', 'channel')
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(zmq_url)
socket.setsockopt_string(zmq.SUBSCRIBE, channel)

redis_server = redis.StrictRedis(
        host=cfg.get('RedisLog', 'host'),
        port=cfg.getint('RedisLog', 'port'),
        db=cfg.getint('RedisLog', 'db'))
serv_coord = redis.StrictRedis(
        host='localhost',
        port=6250,
        db=1) 

channel_proc = "CoordToProcess"
channel_disp = "PicToDisplay"

# server side
pubsub = redis_server.pubsub(ignore_subscribe_messages=True)

while True:
    rdm = random.randint(1,10)
    time.sleep(float(rdm))
    #lux
    lon = random.uniform(5.7373, 6.4823)
    lat = random.uniform(49.4061,49.7449)
    #central eur
    lon = random.uniform(3.936, 9.890)
    lat = random.uniform(47.957, 50.999)
    content = ["rdm "+str(rdm)]
    content = [lat,lon]
    jsonContent = json.dumps(content)
    to_send = { 'name': 'feeder'+str(rdm), 'log': jsonContent }
    redis_server.publish(channel, json.dumps(to_send))
    serv_coord.publish(channel_proc, json.dumps({'lat': float(lat), 'lon': float(lon)}))



while True:
    #FIXME check if sock.recv is blocking
    time.sleep(0.1)
    content = socket.recv()
    print('sending', (content))
    redis_server.publish(channel, content)

    if random.randint(1,10)<5:
        time.sleep(0.5)
        redis_server.publish(channel, content)

    if random.randint(1,10)<5:
        time.sleep(0.5)
        redis_server.publish(channel, content)
