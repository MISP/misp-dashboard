import copy
import datetime
import json
import logging
import math
import os
import random
import time
from collections import OrderedDict

import util


class Trendings_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.cfg = cfg

        # REDIS keys
        self.keyEvent   = "TRENDINGS_EVENTS"
        self.keyCateg   = "TRENDINGS_CATEGS"
        self.keyTag     = "TRENDINGS_TAGS"
        self.keyDisc    = "TRENDINGS_DISC"
        self.keySigh    = "TRENDINGS_SIGHT_sightings"
        self.keyFalse   = "TRENDINGS_SIGHT_false_positive"

        #logger
        logDir = cfg.get('Log', 'directory')
        logfilename = cfg.get('Log', 'filename')
        logPath = os.path.join(logDir, logfilename)
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

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
        self.logger.debug('Added to redis: keyname={}, content={}'.format(keyname, to_save))

    def addTrendingEvent(self, eventName, timestamp):
        self.addGenericTrending(self.keyEvent, eventName, timestamp)

    def addTrendingCateg(self, categName, timestamp):
        self.addGenericTrending(self.keyCateg, categName, timestamp)

    def addTrendingDisc(self, eventName, timestamp):
        self.addGenericTrending(self.keyDisc, eventName, timestamp)

    def addTrendingTags(self, tags, timestamp):
        for tag in tags:
            ordDic = OrderedDict() #keep fields with the same layout in redis
            ordDic['id'] = tag['id']
            ordDic['name'] = tag['name']
            ordDic['colour'] = tag['colour']
            self.addGenericTrending(self.keyTag, ordDic, timestamp)

    def addSightings(self, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)
        keyname = "{}:{}".format(self.keySigh, timestampDate_str)
        self.serv_redis_db.incrby(keyname, 1)
        self.logger.debug('Incrby: keyname={}'.format(keyname))

    def addFalsePositive(self, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)
        keyname = "{}:{}".format(self.keyFalse, timestampDate_str)
        self.serv_redis_db.incrby(keyname, 1)
        self.logger.debug('Incrby: keyname={}'.format(keyname))

    ''' GETTER '''

    def getGenericTrending(self, trendingType, dateS, dateE, topNum=10):
        to_ret = []
        prev_days = (dateE - dateS).days
        for curDate in util.getXPrevDaysSpan(dateE, prev_days):
            keyname = "{}:{}".format(trendingType, util.getDateStrFormat(curDate))
            data = self.serv_redis_db.zrange(keyname, 0, -1, desc=True, withscores=True)
            data = [ [record[0].decode('utf8'), record[1]] for record in data ]
            data = data if data is not None else []
            to_ret.append([util.getTimestamp(curDate), data])
        to_ret = util.sortByTrendingScore(to_ret, topNum=topNum)
        return to_ret

    def getSpecificTrending(self, trendingType, dateS, dateE, specificLabel=''):
        to_ret = []
        prev_days = (dateE - dateS).days
        for curDate in util.getXPrevDaysSpan(dateE, prev_days):
            keyname = "{}:{}".format(trendingType, util.getDateStrFormat(curDate))
            data = self.serv_redis_db.zscore(keyname, specificLabel)
            data = [[specificLabel, data]] if data is not None else []
            to_ret.append([util.getTimestamp(curDate), data])
        return to_ret

    def getTrendingEvents(self, dateS, dateE, specificLabel=None, topNum=None):
        if specificLabel is None:
            return self.getGenericTrending(self.keyEvent, dateS, dateE, topNum=topNum)
        else:
            specificLabel = specificLabel.replace('\\n', '\n'); # reset correctly label with their \n (CR) instead of their char value
            return self.getSpecificTrending(self.keyEvent, dateS, dateE, specificLabel)

    def getTrendingCategs(self, dateS, dateE, topNum=None):
        return self.getGenericTrending(self.keyCateg, dateS, dateE, topNum=topNum)

    # FIXME: Construct this when getting data
    def getTrendingTags(self, dateS, dateE, topNum=12):
        to_ret = []
        prev_days = (dateE - dateS).days
        for curDate in util.getXPrevDaysSpan(dateE, prev_days):
            keyname = "{}:{}".format(self.keyTag, util.getDateStrFormat(curDate))
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
            keyname = "{}:{}".format(self.keySigh, util.getDateStrFormat(curDate))
            sight = self.serv_redis_db.get(keyname)
            sight = 0 if sight is None else int(sight.decode('utf8'))
            keyname = "{}:{}".format(self.keyFalse, util.getDateStrFormat(curDate))
            fp = self.serv_redis_db.get(keyname)
            fp = 0 if fp is None else int(fp.decode('utf8'))
            to_ret.append([util.getTimestamp(curDate), { 'sightings': sight, 'false_positive': fp}])
        return to_ret

    def getTrendingDisc(self, dateS, dateE, topNum=None):
        return self.getGenericTrending(self.keyDisc, dateS, dateE, topNum=topNum)

    def getTypeaheadData(self, dateS, dateE):
        to_ret = {}
        for trendingType in [self.keyEvent, self.keyCateg]:
            allSet = set()
            prev_days = (dateE - dateS).days
            for curDate in util.getXPrevDaysSpan(dateE, prev_days):
                keyname = "{}:{}".format(trendingType, util.getDateStrFormat(curDate))
                data = self.serv_redis_db.zrange(keyname, 0, -1, desc=True)
                for elem in data:
                    allSet.add(elem.decode('utf8'))
            to_ret[trendingType] = list(allSet)
        tags = self.getTrendingTags(dateS, dateE)
        tagSet = set()
        for item in tags:
            theDate, tagList = item
            for tag in tagList:
                tag = tag[0]
                tagSet.add(tag['name'])
        to_ret[self.keyTag] = list(tagSet)
        return to_ret

    # In contrary of getGenericTrending, it regroups items in the format: {item, start: timestamp1, end: timestamp2}
    # so that it can be displayed easily on the timeline.
    def getGenericTrendingOvertime(self, dateS, dateE, choice=None, topNum=0):
        if choice == 'categs':
            trendingType = self.keyCateg
        elif choice == 'tags':
            trendingType = self.keyTag
        else:
            trendingType = self.keyEvent

        dico_items = {}
        to_format = []
        prev_days = (dateE - dateS).days
        # get data
        for curDate in util.getXPrevDaysSpan(dateE, prev_days):
            keyname = "{}:{}".format(trendingType, util.getDateStrFormat(curDate))
            data = self.serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
            data = [ [record[0].decode('utf8'), record[1]] for record in data ]
            data = data if data is not None else []
            to_format.append([util.getTimestamp(curDate), data])

        for timestamp, array in to_format:
            for item, _ in array:
                if item not in dico_items:
                    dico_items[item] = []
                dico_items[item].append(timestamp)

        # sort timestamps in correct order
        for item in dico_items.keys():
            dico_items[item].sort()
        # dico_items have the form: {item: [t1,t2,t4], ...}
        to_ret = []
        ONEDAY = 60*60*24
        for item, timestamps in dico_items.items():
            obj = {'name': item, 'start': timestamps[0], 'end': timestamps[0]+ONEDAY}
            for t in timestamps:
                if t-obj['end'] > ONEDAY: #new entry
                    to_ret.append(copy.deepcopy(obj))
                    obj['start'] = t
                    obj['end'] = t+ONEDAY
                else: # contrinue entry
                    obj['end'] = t+ONEDAY
            to_ret.append(obj)
        return to_ret
