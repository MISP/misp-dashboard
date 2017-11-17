import math, random
import os
import json
import datetime, time

import util

class Trendings_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.cfg = cfg

    ''' SETTER '''

    def addGenericTrending(self, trendingType, data, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)
        keyname = "{}:{}".format(trendingType, timestampDate_str)
        self.serv_redis_db.zincrby(keyname, data, 1)

    def addTrendingEvent(self, eventName, timestamp):
        self.addGenericTrending('TRENDINGS_EVENTS', eventName, timestamp)

    def addTrendingCateg(self, categName, timestamp):
        self.addGenericTrending('TRENDINGS_CATEGS', categName, timestamp)

    def addTrendingTags(self, tags, timestamp):
        for tag in tags:
            self.addGenericTrending('TRENDINGS_TAGS', tag, timestamp)

    def addSightings(self, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)
        keyname = "{}:{}".format("TRENDINGS_SIGHT_sightings", timestampDate_str)
        self.serv_redis_db.incrby(keyname, 1)

    def addFalsePositive(self, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)
        keyname = "{}:{}".format("TRENDINGS_SIGHT_false_positive", timestampDate_str)
        self.serv_redis_db.incrby(keyname, 1)

    ''' GETTER '''

    def getGenericTrending(self, trendingType, dateS, dateE, topNum=12):
        to_ret = []
        prev_days = (dateE - dateS).days
        for curDate in util.getXPrevDaysSpan(dateE, prev_days):
            keyname = "{}:{}".format(trendingType, util.getDateStrFormat(curDate))
            data = self.serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
            data = [ [record[0].decode('utf8'), record[1]] for record in data ]
            data = data if data is not None else []
            to_ret.append([util.getTimestamp(curDate), data])
        return to_ret

    def getTrendingEvents(self, dateS, dateE):
        return self.getGenericTrending('TRENDINGS_EVENTS', dateS, dateE)

    def getTrendingCategs(self, dateS, dateE):
        return self.getGenericTrending('TRENDINGS_CATEGS', dateS, dateE)

    def getTrendingTags(self, dateS, dateE):
        return self.getGenericTrending('TRENDINGS_TAGS', dateS, dateE)
