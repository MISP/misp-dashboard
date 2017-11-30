import math, random
import os
import json
import datetime, time

import util
import contributor_helper

class Users_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.cfg = cfg
        # REDIS keys
        self.keyTimestamp    = "LOGIN_TIMESTAMP"
        self.keyTimestampSet = "LOGIN_TIMESTAMPSET"
        self.keyOrgLog       = "LOGIN_ORG"
        contrib_helper   = contributor_helper.Contributor_helper(serv_redis_db, cfg)
        self.keyContribDay   = contrib_helper.keyDay # Key to get monthly contribution

    def addTemporary(self, org, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateHoursStrFormat(timestampDate)
        keyname_timestamp = "{}:{}".format(self.keyTimestampSet, timestampDate_str)
        self.serv_redis_db.sadd(keyname_timestamp, org)
        self.serv_redis_db.expire(keyname_timestamp, 60*60)

    def hasAlreadyBeenAdded(self, org, timestamp):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateHoursStrFormat(timestampDate)
        keyname_timestamp = "{}:{}".format(self.keyTimestampSet, timestampDate_str)
        orgs = [ org.decode('utf8') for org in self.serv_redis_db.smembers(keyname_timestamp) ]
        if orgs is None:
            return False
        return (org in orgs)

    def add_user_login(self, timestamp, org):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)

        if not self.hasAlreadyBeenAdded(org, timestamp):
            keyname_timestamp = "{}:{}".format(self.keyTimestamp, timestampDate_str)
            self.serv_redis_db.sadd(keyname_timestamp, timestamp)
            self.addTemporary(org, timestamp)

        keyname_org = "{}:{}".format(self.keyOrgLog, timestampDate_str)
        self.serv_redis_db.zincrby(keyname_org, org, 1)

    def getUserLogins(self, date):
        keyname = "{}:{}".format(self.keyTimestamp, util.getDateStrFormat(date))
        timestamps = self.serv_redis_db.smembers(keyname)
        timestamps = [int(timestamp.decode('utf8')) for timestamp in timestamps]
        return timestamps

    def getOrgslogin(self, date, topNum=12):
        keyname = "{}:{}".format(self.keyOrgLog, util.getDateStrFormat(date))
        data = self.serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
        data = [ [record[0].decode('utf8'), record[1]] for record in data ]
        return data

    def getAllLoggedInOrgs(self, date, prev_days=31):
        orgs = set()
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            keyname = "{}:{}".format(self.keyOrgLog, util.getDateStrFormat(curDate))
            data = self.serv_redis_db.zrange(keyname, 0, -1, desc=True, withscores=True)
            for org in data:
                orgs.add(org[0].decode('utf8'))
        return list(orgs)

    def getOrgContribAndLogin(self, date, org, prev_days=31):
        keyname_log = "{}:{}"
        keyname_contrib = "{}:{}"
        data = []
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            log = self.serv_redis_db.zscore(keyname_log.format(self.keyOrgLog, util.getDateStrFormat(curDate)), org)
            log = 0 if log is None else 1
            contrib = self.serv_redis_db.zscore(keyname_contrib.format(self.keyContribDay, util.getDateStrFormat(curDate)), org)
            contrib = 0 if contrib is None else 1
            data.append([log, contrib])
        return data

    def getContribOverLoginScore(self, array):
        totLog = 0
        totContrib = 0
        for log, contrib in array:
            totLog += log
            totContrib += contrib
        if totLog == 0: # avoid div by 0
            totLog = 1
        return totContrib/totLog

    def getTopOrglogin(self, date, maxNum=12, prev_days=7):
        all_logged_in_orgs = self.getAllLoggedInOrgs(date, prev_days)
        data = []
        for org in all_logged_in_orgs:
            orgStatus = self.getOrgContribAndLogin(date, org, prev_days)
            orgScore = self.getContribOverLoginScore(orgStatus)
            data.append([org, orgScore])
        data.sort(key=lambda x: x[1], reverse=True)
        return data[:maxNum]


    def getLoginVSCOntribution(self, date):
        keyname = "{}:{}".format(self.keyContribDay, util.getDateStrFormat(date))
        orgs_contri = self.serv_redis_db.zrange(keyname, 0, -1, desc=True, withscores=False)
        orgs_contri = [ org.decode('utf8') for org in orgs_contri ]
        orgs_login = [ org[0] for org in self.getOrgslogin(date, topNum=0) ]
        contributed_num = 0
        non_contributed_num = 0
        for org in orgs_login:
            if org in orgs_contri:
                contributed_num += 1
            else:
                non_contributed_num +=1
        return [contributed_num, non_contributed_num]


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
                data.append(to_append)
            except KeyError: # no data
                data.append([0 for x in range(24)])
        # swap: punchcard day starts on monday
        data = [data[6]]+data[:6]
        return data

    def getUserLoginsAndContribOvertime(self, date, prev_days=6):
        dico_hours_contrib = {}
        dico_hours = {}
        for curDate in util.getXPrevHoursSpan(date, prev_days*24):
            dico_hours[util.getTimestamp(curDate)] = 0 # populate with empty data
            dico_hours_contrib[util.getTimestamp(curDate)] = 0 # populate with empty data

        for curDate in util.getXPrevDaysSpan(date, prev_days):
            timestamps = self.getUserLogins(curDate)
            keyname = "{}:{}".format(self.keyContribDay, util.getDateStrFormat(curDate))

            orgs_contri = self.serv_redis_db.zrange(keyname, 0, -1, desc=True, withscores=False)
            orgs_contri_num = len(orgs_contri)
            for curDate in util.getHoursSpanOfDate(curDate, adaptToFitCurrentTime=True): #fill hole day
                dico_hours_contrib[util.getTimestamp(curDate)] = orgs_contri_num

            for timestamp in timestamps: # sum occurence during the current hour
                dateTimestamp = datetime.datetime.fromtimestamp(float(timestamp))
                dateTimestamp = dateTimestamp.replace(minute=0, second=0, microsecond=0)
                try:
                    dico_hours[util.getTimestamp(dateTimestamp)] += 1
                except KeyError: # timestamp out of bound (greater than 1 week)
                    pass

        # Format data
        # login
        to_ret = {}
        data = []
        for curDate, occ in dico_hours.items():
            data.append([curDate, occ])
        data.sort(key=lambda x: x[0])
        to_ret['login'] = data
        # contrib
        data = []
        for curDate, occ in dico_hours_contrib.items():
            data.append([curDate, occ])
        data.sort(key=lambda x: x[0])
        to_ret['contrib'] = data

        return to_ret
