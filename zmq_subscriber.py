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
logfilename = cfg.get('Log', 'subscriber_filename')
logPath = os.path.join(logDir, logfilename)
if not os.path.exists(logDir):
    os.makedirs(logDir)
try:
    logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
except PermissionError as error:
    print(error)
    print("Please fix the above and try again.")
    sys.exit(126)
logger = logging.getLogger('zmq_subscriber')

CHANNEL = cfg.get('RedisLog', 'channel')
LISTNAME = cfg.get('RedisLIST', 'listName')

serv_list = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLIST', 'db'),
        decode_responses=True)


###############
## MAIN LOOP ##
###############

def put_in_redis_list(zmq_name, content):
    content = content.decode('utf8')
    to_add = {'zmq_name': zmq_name, 'content': content}
    serv_list.lpush(LISTNAME, json.dumps(to_add))
    logger.debug('Pushed: {}'.format(json.dumps(to_add)))

def main(zmqName, zmqurl):
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(zmqurl)
    socket.setsockopt_string(zmq.SUBSCRIBE, '')

    while True:
        try:
            content = socket.recv()
            put_in_redis_list(zmqName, content)
            print(zmqName, content)
        except KeyboardInterrupt:
            return
        except Exception as e:
            logger.warning('Error:' + str(e))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='A zmq subscriber. It subscribes to a ZMQ then redispatch it to the misp-dashboard')
    parser.add_argument('-n', '--name', required=False, dest='zmqname', help='The ZMQ feed name', default="MISP Standard ZMQ")
    parser.add_argument('-u', '--url', required=False, dest='zmqurl', help='The URL to connect to', default="tcp://localhost:50000")
    args = parser.parse_args()

    try:
        main(args.zmqname, args.zmqurl)
    except redis.exceptions.ResponseError as error:
        print(error)
