import math, random
import os
import json
import datetime, time

import util

class Users_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.cfg = cfg

    def add_user_login(self, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)
        keyname = "{}:{}".format('USER_LOGIN', timestampDate_str)
        self.serv_redis_db.sadd(keyname, timestamp)

    def getUserLogins(self, date):
        keyname = "USER_LOGIN:{}"
        timestamps = self.serv_redis_db.smembers(keyname.format(util.getDateStrFormat(date)))
        timestamps = [int(timestamp.decode('utf8')) for timestamp in timestamps]
        return timestamps

    def getUserLoginsForPunchCard(self, date, prev_days=6):
        week = {}
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            timestamps = self.getUserLogins(curDate)
            day = {}
            for timestamp in timestamps:
                date = datetime.datetime.fromtimestamp(float(timestamp))
                if date.hour not in day:
                    day[date.hour] = 0
                day[date.hour] += 1
            week[curDate.weekday()] = day

        # Format data
        data = []
        for d in range(7):
            try:
                to_append = []
                for h in range(24):
                    try:
                        to_append.append(week[d][h])
                    except KeyError:
                        to_append.append(0)
                # swap 24 and 1. (punchcard starts at 1h)
                temp = to_append[1:]+[to_append[0]]
                data.append(temp)
            except KeyError: # no data
                data.append([0 for x in range(24)])

        return data

    def getUserLoginsOvertime(self, date, prev_days=6):
        dico_hours = {}
        for curDate in util.getXPrevHoursSpan(date, prev_days*24):
            dico_hours[util.getTimestamp(curDate)] = 0 # populate with empty data

        for curDate in util.getXPrevDaysSpan(date, prev_days):
            timestamps = self.getUserLogins(curDate)
            for timestamp in timestamps: # sum occurence during the current hour
                date = datetime.datetime.fromtimestamp(float(timestamp))
                date = date.replace(minute=0, second=0, microsecond=0)
                dico_hours[util.getTimestamp(date)] += 1

        # Format data
        data = []
        for date, occ in dico_hours.items():
            data.append([date, occ])

        data.sort(key=lambda x: x[0])
        return data
