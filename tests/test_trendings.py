#!/usr/bin/env python3.5
import configparser
import redis
import sys,os
import datetime, time
sys.path.append('..')

configfile = 'test_config.cfg'
cfg = configparser.ConfigParser()
cfg.read(configfile)

serv_redis_db = redis.StrictRedis(
        host='localhost',
        port=6260,
        db=1)

from helpers import trendings_helper
trendings_helper = trendings_helper.Trendings_helper(serv_redis_db, cfg)


def wipeRedis():
    serv_redis_db.flushall()

def errorExit():
    sys.exit(1)

def test():
    flag_error = False
    today = datetime.datetime.now()
    now = time.time

    # Events
    event1 = 'test_event_1'
    event2 = 'test_event_2'
    trendings_helper.addTrendingEvent(event1, now())
    trendings_helper.addTrendingEvent(event1, now()+5)
    trendings_helper.addTrendingEvent(event2, now()+10)
    expected_result = [[int(now()), [[event1, 2.0], [event2, 1.0]]]]
    rep = trendings_helper.getTrendingEvents(today, today)
    if rep[0][1] != expected_result[0][1]: #ignore timestamps
        print('getTrendingEvents result not matching')
        flag_error = True

    # Tags
    tag1 = {'id': 'tag1', 'colour': 'blue', 'name': 'tag1Name'}
    tag2 = {'id': 'tag2', 'colour': 'red', 'name': 'tag2Name'}
    trendings_helper.addTrendingTags([tag1], now())
    trendings_helper.addTrendingTags([tag1], now()+5)
    trendings_helper.addTrendingTags([tag2], now()+10)
    expected_result = [[int(now()), [[tag1, 2.0], [tag2, 1.0]]]]
    rep = trendings_helper.getTrendingTags(today, today)
    if rep[0][1] != expected_result[0][1]: #ignore timestamps
        print('getTrendingTags result not matching')
        flag_error = True

    # Sightings
    trendings_helper.addSightings(now())
    trendings_helper.addSightings(now())
    trendings_helper.addFalsePositive(now())
    expected_result = [[1512636256, {'sightings': 2, 'false_positive': 1}]]
    rep = trendings_helper.getTrendingSightings(today, today)
    if rep[0][1] != expected_result[0][1]: #ignore timestamps
        print('getTrendingSightings result not matching')
        flag_error = True
    
    return flag_error

wipeRedis()
if test():
    wipeRedis()
    errorExit()
else:
    wipeRedis()
    print('Trendings tests succeeded')
