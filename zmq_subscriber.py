#!/usr/bin/env python3.5

import time
import zmq
import redis
import random

zmq_url = "tcp://crf.circl.lu:5556"
channel = "102"
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(zmq_url)
socket.setsockopt_string(zmq.SUBSCRIBE, channel)

redis_server = redis.StrictRedis(
        host='localhost',
        port=6250,
        db=0)

# server side
pubsub = redis_server.pubsub(ignore_subscribe_messages=True)

while True:
    time.sleep(0.1)
    content = socket.recv()
    print(content)
    redis_server.publish(channel, content)

    if random.randint(1,10)<5:
        time.sleep(0.5)
        redis_server.publish(channel, content)

    if random.randint(1,10)<5:
        time.sleep(0.5)
        redis_server.publish(channel, content)
