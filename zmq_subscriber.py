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

zmq_url = cfg.get('Redis', 'zmq_url')
zmq_url = "tcp://crf.circl.lu:5556"
channel = cfg.get('Redis', 'channel')
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(zmq_url)
socket.setsockopt_string(zmq.SUBSCRIBE, channel)

redis_server = redis.StrictRedis(
        host=cfg.get('Redis', 'host'),
        port=cfg.getint('Redis', 'port'),
        db=cfg.getint('Redis', 'db'))

# server side
pubsub = redis_server.pubsub(ignore_subscribe_messages=True)

while True:
    rdm = random.randint(1,3)
    time.sleep(float(rdm / 3))
    lat = random.randint(-90,90)
    lon = random.randint(-90,90)
    content = ["rdm "+str(rdm)]
    content = [lat,lon]
    jsonContent = json.dumps(content)
    to_send = { 'name': 'feeder'+str(rdm), 'log': jsonContent }
    redis_server.publish(channel, json.dumps(to_send))

sys.exit(1)


while True:
    #FIXME check if sock.recv is blocking
    time.sleep(0.1)
    content = socket.recv()
    console.log('sending')
    print(content)
    redis_server.publish(channel, content)

    if random.randint(1,10)<5:
        time.sleep(0.5)
        redis_server.publish(channel, content)

    if random.randint(1,10)<5:
        time.sleep(0.5)
        redis_server.publish(channel, content)
