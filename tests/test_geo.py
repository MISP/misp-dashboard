#!/usr/bin/env python3.5
import configparser
import datetime
import os
import sys

import redis

from helpers import geo_helper

sys.path.append('..')

configfile = 'test_config.cfg'
cfg = configparser.ConfigParser()
cfg.read(configfile)

serv_redis_db = redis.StrictRedis(
        host='localhost',
        port=6260,
        db=1)

geo_helper = geo_helper.Geo_helper(serv_redis_db, cfg)

categ = 'Network Activity'

def wipeRedis():
    serv_redis_db.flushall()

def errorExit():
    sys.exit(1)

def test():
    flag_error = False
    today = datetime.datetime.now()

    # IP -> Coord
    supposed_ip = '8.8.8.8'
    geo_helper.getCoordFromIpAndPublish(supposed_ip, categ)
    rep = geo_helper.getTopCoord(today)
    excpected_result = [['{"lat": 37.751, "lon": -97.822, "categ": "Network Activity", "value": "8.8.8.8"}', 1.0]]
    if rep != excpected_result:
        print('ip to coord result not matching')
        flag_error = True

    # gethitmap
    rep = geo_helper.getHitMap(today)
    excpected_result = [['US', 1.0]]
    if rep != excpected_result:
        print('getHitMap result not matching')
        flag_error = True

    # getCoordsByRadius
    rep = geo_helper.getCoordsByRadius(today, today, 0.000, 0.000, '1')
    excpected_result = []
    if rep != excpected_result:
        print('getCoordsByRadius result not matching')
        flag_error = True

    rep = geo_helper.getCoordsByRadius(today, today, 37.750, -97.821, '10')
    excpected_result = [[['{"categ": "Network Activity", "value": "8.8.8.8"}'], [-97.82200008630753, 37.75100012475438]]]
    if rep != excpected_result:
        print('getCoordsByRadius result not matching')
        flag_error = True

    wipeRedis()
    

    # Phone -> Coord
    phoneNumber = '(+352) 247-82000'
    geo_helper.getCoordFromPhoneAndPublish(phoneNumber, categ)
    rep = geo_helper.getTopCoord(datetime.datetime.now())[0]
    excpected_result = ['{"lat": "49.7500", "lon": "6.1667"}', 1.0]
    if rep != excpected_result:
        print('Phone to coord result not matching')
        flag_error = True

    return flag_error

wipeRedis()
if test():
    wipeRedis()
    errorExit()
else:
    wipeRedis()
    print('Geo tests succeeded')
