#!/usr/bin/env python3

import argparse
import configparser
import datetime
import json
import logging
import os
import sys
import time

import redis
import zmq

configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)
logDir = cfg.get('Log', 'directory')
logfilename = cfg.get('Log', 'filename')
logPath = os.path.join(logDir, logfilename)
if not os.path.exists(logDir):
    os.makedirs(logDir)
logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
logger = logging.getLogger('zmq_subscriber')

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
    content = content.decode('utf8')
    to_add = {'zmq_name': zmq_name, 'content': content}
    serv_list.lpush(LISTNAME, json.dumps(to_add))
    logger.debug('Pushed: {}'.format(json.dumps(to_add)))

def main(zmqName):
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(ZMQ_URL)
    socket.setsockopt_string(zmq.SUBSCRIBE, '')

    while True:
        try:
            content = socket.recv()
            put_in_redis_list(zmqName, content)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='A zmq subscriber. It subscribes to a ZNQ then redispatch it to the misp-dashboard')
    parser.add_argument('-n', '--name', required=False, dest='zmqname', help='The ZMQ feed name', default="MISP Standard ZMQ")
    parser.add_argument('-u', '--url', required=False, dest='zmqurl', help='The URL to connect to', default=ZMQ_URL)
    args = parser.parse_args()

    main(args.zmqname)
