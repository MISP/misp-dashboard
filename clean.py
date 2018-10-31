#!/usr/bin/env python3

from pprint import pprint
import os
import redis
import configparser
import argparse


RED="\033[91m"
GREEN="\033[92m"
DEFAULT="\033[0m"


def clean(brutal=False):
    configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg')
    cfg = configparser.ConfigParser()
    cfg.read(configfile)
    host = cfg.get("RedisGlobal", "host")
    port = cfg.getint("RedisGlobal", "port")

    servers = []
    for db in range(0, 4):
        servers.append(redis.Redis(host, port, db=db, decode_responses=True))

    if brutal:
        print(RED+'Brutal mode'+DEFAULT+' selected')
        print('[%s:%s] Cleaning data...' % (host, port))
        cleanBrutal(servers[0])
    else:
        print(GREEN+'Soft mode'+DEFAULT+' selected')
        print('[%s:%s] Cleaning data...' % (host, port))
        cleanSoft(servers)


# Perform a FLUSHALL
def cleanBrutal(server):
    server.flushall()


# Delete all keys independently
def cleanSoft(servers):
    prefix_keys_per_db = {
        0: [], # publish only
        1: [], # publish only (maps)
        3: ['bufferList'],  # queuing
        2: [
            'GEO_COORD:*',
            'GEO_COUNTRY:*',
            'GEO_RAD:*',
            'CONTRIB_DAY:*',
            'CONTRIB_CATEG:*',
            'CONTRIB_LAST:*',
            'CONTRIB_ALL_ORG',
            'CONTRIB_ORG:*',
            'CONTRIB_TROPHY:*',
            'CONTRIB_LAST_AWARDS:*',
            'CONTRIB_ALL_ORG',
            'LOGIN_TIMESTAMP:*',
            'LOGIN_ORG:*',
            'LOGIN_ALL_ORG',
            'TRENDINGS_EVENTS:*',
            'TRENDINGS_CATEGS:*',
            'TRENDINGS_TAGS:*',
            'TRENDINGS_DISC:*',
            'TRENDINGS_SIGHT_sightings:*',
            'TRENDINGS_SIGHT_false_positive:*',
            'TEMP_CACHE_LIVE:*',
        ]
    }

    for db, keys in prefix_keys_per_db.items():
        serv = servers[db]
        for k in keys:
            # fetch all keys on the db
            key_to_del = serv.keys(k)
            # delete all existing keys
            if len(key_to_del) > 0:
                serv.delete(*tuple(key_to_del))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Clean data stored in the redis server specified in the configuration file')
    parser.add_argument("-b", "--brutal", default=False, action="store_true", help="Perfom a FLUSHALL on the redis database. If not set, will use a soft method to delete only keys used by MISP-Dashboard.")
    args = parser.parse_args()
    clean(args.brutal)
    print(GREEN+'Done.'+DEFAULT)
