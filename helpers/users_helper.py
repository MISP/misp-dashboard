import datetime
import json
import logging
import math
import os
import random
import time

import util

from . import contributor_helper


class Users_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.cfg = cfg
        # REDIS keys
        self.keyTimestamp     = "LOGIN_TIMESTAMP"
        self.keyOrgLog        = "LOGIN_ORG"
        self.keyContribDay    = contributor_helper.KEYDAY # Key to get monthly contribution
        self.keyAllOrgLog     = "LOGIN_ALL_ORG" # Key to get all organisation that logged in

        #logger
        logDir = cfg.get('Log', 'directory')
        logfilename = cfg.get('Log', 'helpers_filename')
        logPath = os.path.join(logDir, logfilename)
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        try:
            logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
        except PermissionError as error:
            print(error)
            print("Please fix the above and try again.")
            sys.exit(126)
        self.logger = logging.getLogger(__name__)

    def add_user_login(self, timestamp, org, email=''):
        timestampDate = datetime.datetime.fromtimestamp(float(timestamp))
        timestampDate_str = util.getDateStrFormat(timestampDate)

        keyname_timestamp = "{}:{}".format(self.keyTimestamp, org)
        self.serv_redis_db.zadd(keyname_timestamp, timestamp, timestamp)
        self.logger.debug('Added to redis: keyname={}, org={}'.format(keyname_timestamp, timestamp))

        keyname_org = "{}:{}".format(self.keyOrgLog, timestampDate_str)
        self.serv_redis_db.zincrby(keyname_org, org, 1)
        self.logger.debug('Added to redis: keyname={}, org={}'.format(keyname_org, org))

        self.serv_redis_db.sadd(self.keyAllOrgLog, org)
        self.logger.debug('Added to redis: keyname={}, org={}'.format(self.keyAllOrgLog, org))

    def getAllOrg(self):
        temp = self.serv_redis_db.smembers(self.keyAllOrgLog)
        return [ org.decode('utf8') for org in temp ]

    # return: All timestamps for one org for the spanned time or not
    def getDates(self, org, date=None):
        keyname = "{}:{}".format(self.keyTimestamp, org)
        timestamps = self.serv_redis_db.zrange(keyname, 0, -1, desc=True, withscores=True)
        if date is None:
            to_return = [ datetime.datetime.fromtimestamp(float(t[1])) for t in timestamps ]
        else:
            to_return = []
            for t in timestamps:
                t = datetime.datetime.fromtimestamp(float(t[1]))
                if util.getDateStrFormat(t) == util.getDateStrFormat(date): #same day
                    to_return.append(t)
                elif util.getDateStrFormat(t) > util.getDateStrFormat(date):
                    continue # timestamps should be sorted, skipping to reach wanted date
                else:
                    break # timestamps should be sorted, no need to process anymore
        return to_return


    # return: All dates for all orgs, if date is not supplied, return for all dates
    def getUserLogins(self, date=None):
        # get all orgs and retrieve their timestamps
        dates = []
        for org in self.getAllOrg():
            keyname = "{}:{}".format(self.keyOrgLog, org)
            dates += self.getDates(org, date)
        return dates

    # return: All orgs that logged in for the time spanned
    def getAllLoggedInOrgs(self, date, prev_days=31):
        orgs = set()
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            keyname = "{}:{}".format(self.keyOrgLog, util.getDateStrFormat(curDate))
            data = self.serv_redis_db.zrange(keyname, 0, -1, desc=True)
            for org in data:
                orgs.add(org.decode('utf8'))
        return list(orgs)

    # return: list composed of the number of [log, contrib] for one org for the time spanned
    def getOrgContribAndLogin(self, date, org, prev_days=31):
        keyname_log = "{}:{}"
        keyname_contrib = "{}:{}"
        data = []
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            log = self.serv_redis_db.zscore(keyname_log.format(self.keyOrgLog, util.getDateStrFormat(curDate)), org)
            log = 0 if log is None else 1
            contrib = self.serv_redis_db.zscore(keyname_contrib.format(self.keyContribDay, util.getDateStrFormat(curDate)), org)
            contrib = 0 if contrib is None else contrib
            data.append([log, contrib])
        return data

    # return: the computed ratio of contribution/login for a given array
    def getContribOverLoginScore(self, array):
        totLog = 0
        totContrib = 0
        for log, contrib in array:
            totLog += log
            totContrib += contrib
        if totLog == 0: # avoid div by 0
            totLog = 1
        return totContrib/totLog

    # return: list of org having the greatest ContribOverLoginScore for the time spanned
    def getTopOrglogin(self, date, maxNum=12, prev_days=7):
        all_logged_in_orgs = self.getAllLoggedInOrgs(date, prev_days)
        data = []
        for org in all_logged_in_orgs:
            orgStatus = self.getOrgContribAndLogin(date, org, prev_days)
            orgScore = self.getContribOverLoginScore(orgStatus)
            data.append([org, orgScore])
        data.sort(key=lambda x: x[1], reverse=True)
        return data[:maxNum]


    # return: array composed of [number of org that contributed, number of org that logged in without contribution]
    #         for the spanned time
    def getLoginVSCOntribution(self, date):
        keyname = "{}:{}".format(self.keyContribDay, util.getDateStrFormat(date))
        orgs_contri = self.serv_redis_db.zrange(keyname, 0, -1, desc=True, withscores=False)
        orgs_contri = [ org.decode('utf8') for org in orgs_contri ]
        orgs_login = [ org for org in self.getAllLoggedInOrgs(date, prev_days=0) ]
        contributed_num = 0
        non_contributed_num = 0
        for org in orgs_login:
            if org in orgs_contri:
                contributed_num += 1
            else:
                non_contributed_num +=1
        return [contributed_num, non_contributed_num]


    # return: list of day where day is a list of the number of time users logged in during an hour
    def getUserLoginsForPunchCard(self, date, org=None, prev_days=6):
        week = {}
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            if org is None:
                dates = self.getUserLogins(curDate)
            else:
                dates = self.getDates(org, date=curDate)
            day = {}
            for date in dates:
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
        # swap: punchcard day starts on sunday
        data = [data[6]]+data[:6]
        return data

    # return: a dico of the form {login: [[timestamp, count], ...], contrib: [[timestamp, 1/0], ...]}
    #         either for all orgs or the supplied one
    def getUserLoginsAndContribOvertime(self, date, org=None, prev_days=6):
        dico_hours_contrib = {}
        dico_hours = {}
        for curDate in util.getXPrevHoursSpan(date, prev_days*24):
            dico_hours[util.getTimestamp(curDate)] = 0 # populate with empty data
            dico_hours_contrib[util.getTimestamp(curDate)] = 0 # populate with empty data

        for curDate in util.getXPrevDaysSpan(date, prev_days):
            if org is None:
                dates = self.getUserLogins(curDate)
            else:
                dates = self.getDates(org, date=curDate)
            keyname = "{}:{}".format(self.keyContribDay, util.getDateStrFormat(curDate))

            if org is None:
                orgs_contri = self.serv_redis_db.zrange(keyname, 0, -1, desc=True, withscores=True)
                orgs_contri_num = 0
                for _, count in orgs_contri:
                    orgs_contri_num += count
            else:
                orgs_contri_num = self.serv_redis_db.zscore(keyname, org)
                orgs_contri_num = orgs_contri_num if orgs_contri_num is not None else 0

            for curDate in util.getHoursSpanOfDate(curDate, adaptToFitCurrentTime=True): #fill hole day
                dico_hours_contrib[util.getTimestamp(curDate)] = orgs_contri_num

            for d in dates: # sum occurence during the current hour
                dateTimestamp = d.replace(minute=0, second=0, microsecond=0)
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
