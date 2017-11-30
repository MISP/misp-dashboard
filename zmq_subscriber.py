#!/usr/bin/env python3.5

import time, datetime
from pprint import pprint
import zmq
import redis
import configparser
import argparse
import os
import sys
import json

configfile = os.path.join(os.environ['DASH_CONFIG'], 'config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

ZMQ_URL = cfg.get('RedisGlobal', 'zmq_url')
CHANNEL = cfg.get('RedisLog', 'channel')
LISTNAME = cfg.get('RedisLIST', 'listName')

serv_list = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLIST', 'db'))


###############
## MAIN LOOP ##
###############

def put_in_redis_list(zmq_name, content):
    to_add = {'zmq_name': zmq_name, 'content': content}
    serv_list.lpush(LISTNAME, json.dumps(content))

def main(zmqName):
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(ZMQ_URL)
    socket.setsockopt_string(zmq.SUBSCRIBE, '')

    while True:
        try:
            content = socket.recv()
            content.replace(b'\n', b'') # remove \n...
            put_in_redis_list(zmqName, content)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='A zmq subscriber. It subscribe to a ZNQ then redispatch it to the misp-dashboard')
    parser.add_argument('-n', '--name', required=False, dest='zmqname', help='The ZMQ feed name', default="MISP Standard ZMQ")
    parser.add_argument('-u', '--url', required=False, dest='zmqurl', help='The URL to connect to', default=ZMQ_URL)
    args = parser.parse_args()

    main(args.zmqname)
