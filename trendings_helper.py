import math, random
import os
import json
import datetime, time
from collections import OrderedDict

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
        if isinstance(data, OrderedDict):
            to_save = json.dumps(data)
        else:
            to_save = data
        self.serv_redis_db.zincrby(keyname, to_save, 1)

    def addTrendingEvent(self, eventName, timestamp):
        self.addGenericTrending('TRENDINGS_EVENTS', eventName, timestamp)

    def addTrendingCateg(self, categName, timestamp):
        self.addGenericTrending('TRENDINGS_CATEGS', categName, timestamp)

    def addTrendingDisc(self, eventName, timestamp):
        self.addGenericTrending('TRENDINGS_DISC', eventName, timestamp)

    def addTrendingTags(self, tags, timestamp):
        for tag in tags:
            ordDic = OrderedDict() #keep fields with the same layout in redis
            ordDic['id'] = tag['id']
            ordDic['name'] = tag['name']
            ordDic['colour'] = tag['colour']
            self.addGenericTrending('TRENDINGS_TAGS', ordDic, timestamp)

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

    def getTrendingTags(self, dateS, dateE, topNum=12):
        to_ret = []
        prev_days = (dateE - dateS).days
        for curDate in util.getXPrevDaysSpan(dateE, prev_days):
            keyname = "{}:{}".format('TRENDINGS_TAGS', util.getDateStrFormat(curDate))
            data = self.serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
            data = [ [record[0].decode('utf8'), record[1]] for record in data ]
            data = data if data is not None else []
            temp = []
            for jText, score in data:
                temp.append([json.loads(jText), score])
            data = temp
            to_ret.append([util.getTimestamp(curDate), data])
        return to_ret

    def getTrendingSightings(self, dateS, dateE):
        to_ret = []
        prev_days = (dateE - dateS).days
        for curDate in util.getXPrevDaysSpan(dateE, prev_days):
            keyname = "{}:{}".format("TRENDINGS_SIGHT_sightings", util.getDateStrFormat(curDate))
            sight = self.serv_redis_db.get(keyname)
            sight = 0 if sight is None else int(sight.decode('utf8'))
            keyname = "{}:{}".format("TRENDINGS_SIGHT_false_positive", util.getDateStrFormat(curDate))
            fp = self.serv_redis_db.get(keyname)
            fp = 0 if fp is None else int(fp.decode('utf8'))
            to_ret.append([util.getTimestamp(curDate), { 'sightings': sight, 'false_positive': fp}])
        return to_ret

    def getTrendingDisc(self, dateS, dateE):
        return self.getGenericTrending('TRENDINGS_DISC', dateS, dateE)
