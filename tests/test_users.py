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

from helpers import users_helper
users_helper = users_helper.Users_helper(serv_redis_db, cfg)


def wipeRedis():
    serv_redis_db.flushall()

def errorExit():
    sys.exit(1)

# return if array are equal even if they are unordered
def checkArrayEquality(arr1, arr2):
    temp = arr2[:]
    for i in arr1:
        if i in temp:
            temp.remove(i)
        else:
            return False
    return True


def test():
    flag_error = False
    now = int(time.time())
    today = datetime.datetime.fromtimestamp(now)
    twoDayAgo = today - datetime.timedelta(days=2)
    DAY = 60*60*24
    org = 'TEST_ORG'
    org2 = 'TEST_ORG2'

    # logged in dates
    users_helper.add_user_login(now, org)
    users_helper.add_user_login(now+5, org)
    users_helper.add_user_login(now-DAY*2, org)
    expected_result = [datetime.datetime.fromtimestamp(now-DAY*2), datetime.datetime.fromtimestamp(now+5), datetime.datetime.fromtimestamp(now)]
    rep = users_helper.getDates(org)

    if not checkArrayEquality(rep, expected_result):
        print('getDates result not matching for all dates')
        flag_error = True
    expected_result = [datetime.datetime.fromtimestamp(now+5), datetime.datetime.fromtimestamp(now)]
    rep = users_helper.getDates(org, datetime.datetime.now())
    if not checkArrayEquality(rep, expected_result):
        print('getDates result not matching for query 1')
        flag_error = True
    expected_result = []
    rep = users_helper.getDates(org, datetime.datetime.now()-datetime.timedelta(days=7))
    if not checkArrayEquality(rep, expected_result):
        print('getDates result not matching for query 2')
        flag_error = True
    
    # all logged orgs
    users_helper.add_user_login(now, org2)
    expected_result = [datetime.datetime.fromtimestamp(now+5), datetime.datetime.fromtimestamp(now), datetime.datetime.fromtimestamp(now)]
    rep = users_helper.getUserLogins(datetime.datetime.now())
    if not checkArrayEquality(rep, expected_result):
        print('getUserLogins result not matching')
        flag_error = True

    # all logged in org
    expected_result = [org, org2]
    rep = users_helper.getAllLoggedInOrgs(datetime.datetime.fromtimestamp(now+5), prev_days=7)
    if not checkArrayEquality(rep, expected_result):
        print('getAllLoggedInOrgs result not matching')
        flag_error = True

    # punchcard
    expected_result = [ [0 for x in range(24)] for y in range(7)]
    # set correct values
    day = today.weekday()
    hour = today.hour
    expected_result[day][hour] = 3
    day = twoDayAgo.weekday()
    hour = twoDayAgo.hour
    expected_result[day][hour] = 1
    # swap: punchcard day starts on sunday
    expected_result = [expected_result[6]]+expected_result[:6]
    rep = users_helper.getUserLoginsForPunchCard(datetime.datetime.fromtimestamp(now), org=None, prev_days=6)
    if not checkArrayEquality(rep, expected_result):
        print('getUserLoginsForPunchCard result not matching')
        flag_error = True

    # overtime
    rep = users_helper.getUserLoginsAndContribOvertime(datetime.datetime.fromtimestamp(now), org=None, prev_days=6)
    t1 = all([tab[1]==0 for tab in rep['contrib']]) # no contribution
    t2 = [True for tab in rep['login'] if tab[1] == 3]
    t2 = t2[0] and len(t2)==1 # one login at 3, others at 0
    if not (t1 and t2):
        print('getUserLoginsAndContribOvertime result not matching')
        flag_error = True
    




    return flag_error

wipeRedis()
if test():
    wipeRedis()
    errorExit()
else:
    wipeRedis()
    print('Users tests succeeded')
