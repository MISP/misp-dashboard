import util
from util import getZrange
import math, random
import time
import os
import configparser
import json
import datetime
import redis

import util
import users_helper
KEYDAY = "CONTRIB_DAY" # To be used by other module

class Contributor_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.serv_log = redis.StrictRedis(
            host=cfg.get('RedisGlobal', 'host'),
            port=cfg.getint('RedisGlobal', 'port'),
            db=cfg.getint('RedisLog', 'db'))
        self.cfg = cfg
        self.cfg_org_rank = configparser.ConfigParser()
        self.cfg_org_rank.read(os.path.join(os.environ['DASH_CONFIG'], 'ranking.cfg'))
        self.CHANNEL_LASTAWARDS = cfg.get('RedisLog', 'channelLastAwards')
        self.CHANNEL_LASTCONTRIB = cfg.get('RedisLog', 'channelLastContributor')
        self.users_helper = users_helper.Users_helper(serv_redis_db, cfg)

        #honorBadge
        self.honorBadgeNum = len(self.cfg_org_rank.options('HonorBadge'))
        self.heavilyCount = self.cfg_org_rank.getint('rankRequirementsMisc', 'heavilyCount')
        self.recentDays = self.cfg_org_rank.getint('rankRequirementsMisc', 'recentDays')
        self.regularlyDays = self.cfg_org_rank.getint('rankRequirementsMisc', 'regularlyDays')

        self.org_honor_badge_title = {}
        for badgeNum in range(1, self.honorBadgeNum+1): #get Num of honorBadge
            self.org_honor_badge_title[badgeNum] = self.cfg_org_rank.get('HonorBadge', str(badgeNum))

        self.trophyMapping = json.loads(self.cfg_org_rank.get('TrophyDifficulty', 'trophyMapping'))
        self.trophyNum = len(self.cfg_org_rank.options('HonorTrophy'))-1 #0 is not a trophy
        self.categories_in_trophy = json.loads(self.cfg_org_rank.get('HonorTrophyCateg', 'categ'))
        self.trophy_title = {}
        for trophyNum in range(0, len(self.cfg_org_rank.options('HonorTrophy'))): #get Num of trophy
            self.trophy_title[trophyNum] = self.cfg_org_rank.get('HonorTrophy', str(trophyNum))

        #GLOBAL RANKING
        self.org_rank_maxLevel = self.cfg_org_rank.getint('rankTitle', 'maxLevel')
        self.org_rank = {}
        for rank in range(1, self.org_rank_maxLevel+1):
            self.org_rank[rank] = self.cfg_org_rank.get('rankTitle', str(rank))
        self.org_rank_requirement_pnts = {}
        for rank in range(1, self.org_rank_maxLevel+1):
            self.org_rank_requirement_pnts[rank] = self.cfg_org_rank.getint('rankRequirementsPnts', str(rank))
        self.org_rank_requirement_text = {}
        for rank in range(1, self.org_rank_maxLevel+1):
            self.org_rank_requirement_text[rank] = self.cfg_org_rank.get('rankRequirementsText', str(rank))
        self.org_rank_additional_info = json.loads(self.cfg_org_rank.get('additionalInfo', 'textsArray'))

        #WEB STUFF
        self.misp_web_url = cfg.get('RedisGlobal', 'misp_web_url')
        self.MAX_NUMBER_OF_LAST_CONTRIBUTOR = cfg.getint('CONTRIB', 'max_number_of_last_contributor')
        self.categories_in_datatable = json.loads(self.cfg_org_rank.get('monthlyRanking', 'categories_in_datatable'))

        #MONTHLY RANKING
        self.default_pnts_per_contribution = json.loads(self.cfg_org_rank.get('monthlyRanking', 'default_pnts_per_contribution'))
        temp = json.loads(self.cfg_org_rank.get('monthlyRanking', 'pnts_per_contribution'))
        self.DICO_PNTS_REWARD = {}
        for categ, pnts in temp:
            self.DICO_PNTS_REWARD[categ] = pnts
        # fill other categ with default points
        for categ in self.categories_in_datatable:
            if categ in self.DICO_PNTS_REWARD:
                continue
            else:
                self.DICO_PNTS_REWARD[categ] = self.default_pnts_per_contribution

        self.rankMultiplier = self.cfg_org_rank.getfloat('monthlyRanking' ,'rankMultiplier')
        self.levelMax = self.cfg_org_rank.getfloat('monthlyRanking' ,'levelMax')

        # REDIS KEYS
        self.keyDay         = KEYDAY
        self.keyCateg       = "CONTRIB_CATEG"
        self.keyLastContrib = "CONTRIB_LAST"
        self.keyAllOrg      = "CONTRIB_ALL_ORG"
        self.keyContribReq  = "CONTRIB_ORG"
        self.keyTrophy      = "CONTRIB_TROPHY"
        self.keyLastAward   = "CONTRIB_LAST_AWARDS"


    ''' HELPER '''
    def getOrgLogoFromMISP(self, org):
        return "{}/img/orgs/{}.png".format(self.misp_web_url, org)

    def addContributionToCateg(self, date, categ, org, count=1):
        today_str = util.getDateStrFormat(date)
        keyname = "{}:{}:{}".format(self.keyCateg, today_str, categ)
        self.serv_redis_db.zincrby(keyname, org, count)

    def publish_log(self, zmq_name, name, content, channel=""):
        to_send = { 'name': name, 'log': json.dumps(content), 'zmqName': zmq_name }
        self.serv_log.publish(channel, json.dumps(to_send))

    ''' HANDLER '''
    #pntMultiplier if one contribution rewards more than others. (e.g. shighting may gives more points than editing)
    def handleContribution(self, zmq_name, org, contribType, categ, action, pntMultiplier=1, eventTime=datetime.datetime.now(), isLabeled=False):
        if action in ['edit', None]:
            pass
            #return #not a contribution?
    
        now = datetime.datetime.now()
        nowSec = int(time.time())
        pnts_to_add = self.default_pnts_per_contribution
    
        # if there is a contribution, there is a login (even if ti comes from the API)
        self.users_helper.add_user_login(nowSec, org)
    
        # is a valid contribution
        if categ is not None:
            try:
                pnts_to_add = self.DICO_PNTS_REWARD[util.noSpaceLower(categ)]
            except KeyError:
                pnts_to_add = self.default_pnts_per_contribution
            pnts_to_add *= pntMultiplier
    
            util.push_to_redis_zset(self.serv_redis_db, self.keyDay, org, count=pnts_to_add)
            #CONTRIB_CATEG retain the contribution per category, not the point earned in this categ
            util.push_to_redis_zset(self.serv_redis_db, self.keyCateg, org, count=1, endSubkey=':'+util.noSpaceLower(categ))
            self.publish_log(zmq_name, 'CONTRIBUTION', {'org': org, 'categ': categ, 'action': action, 'epoch': nowSec }, channel=self.CHANNEL_LASTCONTRIB)
        else:
            categ = ""
    
        self.serv_redis_db.sadd(self.keyAllOrg, org)
    
        keyname = "{}:{}".format(self.keyLastContrib, util.getDateStrFormat(now))
        self.serv_redis_db.zadd(keyname, nowSec, org)
        self.serv_redis_db.expire(keyname, util.ONE_DAY*7) #expire after 7 day
    
        awards_given = self.updateOrgContributionRank(org, pnts_to_add, action, contribType, eventTime=datetime.datetime.now(), isLabeled=isLabeled, categ=util.noSpaceLower(categ))
    
        for award in awards_given:
            # update awards given
            keyname = "{}:{}".format(self.keyLastAward, util.getDateStrFormat(now))
            self.serv_redis_db.zadd(keyname, nowSec, json.dumps({'org': org, 'award': award, 'epoch': nowSec }))
            self.serv_redis_db.expire(keyname, util.ONE_DAY*7) #expire after 7 day
            # publish
            self.publish_log(zmq_name, 'CONTRIBUTION', {'org': org, 'award': award, 'epoch': nowSec }, channel=self.CHANNEL_LASTAWARDS)

    ''' CONTRIBUTION RANK '''
    def getOrgContributionTotalPoints(self, org):
        keyname = '{mainKey}:{org}:{orgCateg}'
        pnts = self.serv_redis_db.get(keyname.format(mainKey=self.keyContribReq, org=org, orgCateg='points'))
        if pnts is None:
            pnts = 0
        else:
            pnts = int(pnts.decode('utf8'))
        return pnts

    # return: [final_rank, requirement_fulfilled, requirement_not_fulfilled]
    def getOrgContributionRank(self, org):
        keyname = '{mainKey}:{org}:{orgCateg}'
        final_rank = 0
        requirement_fulfilled = []
        requirement_not_fulfilled = []
        for i in range(1, self.org_rank_maxLevel+1):
            key = keyname.format(mainKey=self.keyContribReq, org=org, orgCateg='CONTRIB_REQ_'+str(i))
            if self.serv_redis_db.get(key) is None: #non existing
                requirement_not_fulfilled.append(i)
            else:
                requirement_fulfilled.append(i)
                final_rank += 1
        #num_of_previous_req_not_fulfilled = len([x for x in requirement_not_fulfilled if x<final_rank])
        #final_rank = final_rank -  num_of_previous_req_not_fulfilled
        final_rank = len(requirement_fulfilled)
        return {'final_rank': final_rank, 'req_fulfilled': requirement_fulfilled, 'req_not_fulfilled': requirement_not_fulfilled}

    def giveContribRankToOrg(self, org, rankNum):
        keyname = '{mainKey}:{org}:{orgCateg}'
        self.serv_redis_db.set(keyname.format(mainKey=self.keyContribReq, org=org, orgCateg='CONTRIB_REQ_'+str(rankNum)), 1)

    def removeContribRankFromOrg(self, org, rankNum):
        keyname = '{mainKey}:{org}:{orgCateg}'
        self.serv_redis_db.delete(keyname.format(mainKey=self.keyContribReq, org=org, orgCateg='CONTRIB_REQ_'+str(rankNum)))

    # 1 for fulfilled, 0 for not fulfilled, -1 for not relevant
    def getCurrentContributionStatus(self, org):
        temp = self.getOrgContributionRank(org)
        final_rank = temp['final_rank']
        requirement_fulfilled = temp['req_fulfilled']
        requirement_not_fulfilled = temp['req_not_fulfilled']
        to_ret = {}
        for i in range(1, self.org_rank_maxLevel+1):
            if i in requirement_fulfilled:
                to_ret[i] = 1
            elif i in requirement_not_fulfilled and i<=final_rank:
                to_ret[i] = 0
            else:
                to_ret[i] = -1
        return {'rank': final_rank, 'status': to_ret, 'totPoints': self.getOrgContributionTotalPoints(org)}

    # return the awards given to the organisation
    def updateOrgContributionRank(self, orgName, pnts_to_add, action, contribType, eventTime, isLabeled, categ=""):
        ContributionStatus = self.getCurrentContributionStatus(orgName)
        oldContributionStatus = ContributionStatus['status']
        oldHonorBadges = self.getOrgHonorBadges(orgName)
        oldTrophy = self.getOrgTrophies(orgName)
        keyname = self.keyContribReq+':{org}:{orgCateg}'
        # update total points
        totOrgPnts = self.serv_redis_db.incrby(keyname.format(org=orgName, orgCateg='points'), pnts_to_add)

        #FIXME TEMPORARY, JUST TO TEST IF IT WORKS CORRECLTY
        self.giveTrophyPointsToOrg(orgName, categ, 1)

        # update date variables
        if contribType == 'Attribute':
            attributeWeekCount = self.serv_redis_db.incrby(keyname.format(org=orgName, orgCateg='ATTR_WEEK_COUNT'), 1)
            self.serv_redis_db.expire(keyname.format(org=orgName, orgCateg='ATTR_WEEK_COUNT'), util.ONE_DAY*7)

        if contribType == 'Proposal':
            proposalWeekCount = self.serv_redis_db.incrby(keyname.format(org=orgName, orgCateg='PROP_WEEK_COUNT'), 1)
            self.serv_redis_db.expire(keyname.format(org=orgName, orgCateg='PROP_WEEK_COUNT'), util.ONE_DAY*7)
            addContributionToCateg(datetime.datetime.now(), 'proposal')

        if contribType == 'Sighting':
            sightingWeekCount = self.serv_redis_db.incrby(keyname.format(org=orgName, orgCateg='SIGHT_WEEK_COUNT'), 1)
            self.serv_redis_db.expire(keyname.format(org=orgName, orgCateg='SIGHT_WEEK_COUNT'), util.ONE_DAY*7)
            self.addContributionToCateg(datetime.datetime.now(), 'sighting', orgName)

        if contribType == 'Discussion':
            self.addContributionToCateg(datetime.datetime.now(), 'discussion', orgName)

        if contribType == 'Event':
            eventWeekCount = self.serv_redis_db.incrby(keyname.format(org=orgName, orgCateg='EVENT_WEEK_COUNT'), 1)
            self.serv_redis_db.expire(keyname.format(org=orgName, orgCateg='EVENT_WEEK_COUNT'), util.ONE_DAY*7)

            eventMonthCount = self.serv_redis_db.incrby(keyname.format(org=orgName, orgCateg='EVENT_MONTH_COUNT'), 1)
            self.serv_redis_db.expire(keyname.format(org=orgName, orgCateg='EVENT_MONTH_COUNT'), util.ONE_DAY*7)

        # getRequirement parameters
        heavilyCount = self.heavilyCount
        recentDays = self.recentDays
        regularlyDays = self.regularlyDays
        isRecent = (datetime.datetime.now() - eventTime).days > recentDays

        #update contribution Requirement
        contrib = [] #[[contrib_level, contrib_ttl], [], ...]
        if totOrgPnts >= self.org_rank_requirement_pnts[1] and contribType == 'Sighting':
            #[contrib_level, contrib_ttl]
            contrib.append([1, util.ONE_DAY*365])
        if totOrgPnts >= self.org_rank_requirement_pnts[2] and contribType == 'Attribute' or contribType == 'Object':
            contrib.append([2, util.ONE_DAY*365])
        if totOrgPnts >= self.org_rank_requirement_pnts[3] and contribType == 'Proposal' or contribType == 'Discussion':
            contrib.append([3, util.ONE_DAY*365])
        if totOrgPnts >= self.org_rank_requirement_pnts[4] and contribType == 'Sighting' and isRecent:
            contrib.append([4, util.ONE_DAY*recentDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[5] and contribType == 'Proposal' and isRecent:
            contrib.append([5, util.ONE_DAY*recentDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[6] and contribType == 'Event':
            contrib.append([6, util.ONE_DAY*365])
        if totOrgPnts >= self.org_rank_requirement_pnts[7] and contribType == 'Event' and eventMonthCount>=1:
            contrib.append([7, util.ONE_DAY*recentDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[8] and contribType == 'Event' and eventWeekCount>=1:
            contrib.append([8, util.ONE_DAY*regularlyDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[9] and contribType == 'Event' and isLabeled:
            contrib.append([9, util.ONE_DAY*regularlyDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[10] and contribType == 'Sighting' and sightingWeekCount>heavilyCount:
            contrib.append([10, util.ONE_DAY*regularlyDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[11] and (contribType == 'Attribute' or contribType == 'Object') and attributeWeekCount>heavilyCount:
            contrib.append([11, util.ONE_DAY*regularlyDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[12] and contribType == 'Proposal' and proposalWeekCount>heavilyCount:
            contrib.append([12, util.ONE_DAY*regularlyDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[13] and contribType == 'Event' and eventWeekCount>heavilyCount:
            contrib.append([13, util.ONE_DAY*regularlyDays])
        if totOrgPnts >= self.org_rank_requirement_pnts[14] and contribType == 'Event' and eventWeekCount>heavilyCount  and isLabeled:
            contrib.append([14, util.ONE_DAY*regularlyDays])

        for rankReq, ttl in contrib:
            self.serv_redis_db.set(keyname.format(org=orgName, orgCateg='CONTRIB_REQ_'+str(rankReq)), 1)
            self.serv_redis_db.expire(keyname.format(org=orgName, orgCateg='CONTRIB_REQ_'+str(rankReq)), ttl)

        ContributionStatus = self.getCurrentContributionStatus(orgName)
        newContributionStatus = ContributionStatus['status']
        newHonorBadges = self.getOrgHonorBadges(orgName)
        newTrophy = self.getOrgTrophies(orgName)

        # awards to publish
        awards_given = []
        for i in newContributionStatus.keys():
            if oldContributionStatus[i] < newContributionStatus[i] and i != ContributionStatus['rank']:
                awards_given.append(['contribution_status', i])

        for badgeNum in newHonorBadges:
            if badgeNum not in  oldHonorBadges:
                awards_given.append(['badge', badgeNum])

        temp = {}
        for item in oldTrophy:
            categ = item['categ']
            rank = item['trophy_true_rank']
            temp[categ] = rank
        for item in newTrophy:
            categ = item['categ']
            rank = item['trophy_true_rank']
            try:
                oldCategRank = temp[categ]
            except KeyError:
                oldCategRank = 0
            if rank > oldCategRank:
                awards_given.append(['trophy', [categ, rank]])

        return awards_given

    ''' HONOR BADGES '''
    def getOrgHonorBadges(self, org):
        keyname = '{mainKey}:{org}:{orgCateg}'
        honorBadge = []
        for i in range(1, self.honorBadgeNum+1):
            key = keyname.format(mainKey=self.keyContribReq, org=org, orgCateg='BADGE_'+str(i))
            if self.serv_redis_db.get(key) is not None: #existing
                honorBadge.append(i)
        return honorBadge

    def giveBadgeToOrg(self, org, badgeNum):
        keyname = '{mainKey}:{org}:{orgCateg}'
        self.serv_redis_db.set(keyname.format(mainKey=self.keyContribReq, org=org, orgCateg='BADGE_'+str(badgeNum)), 1)

    def removeBadgeFromOrg(self, org, badgeNum):
        keyname = '{mainKey}:{org}:{orgCateg}'
        self.serv_redis_db.delete(keyname.format(mainKey=self.keyContribReq, org=org, orgCateg='BADGE_'+str(badgeNum)))

    ''' TROPHIES '''
    def getOrgTrophies(self, org):
        self.getAllOrgsTrophyRanking()
        keyname = '{mainKey}:{orgCateg}'
        trophy = []
        for categ in self.categories_in_trophy:
            key = keyname.format(mainKey=self.keyTrophy, orgCateg=categ)
            totNum = self.serv_redis_db.zcard(key)
            if totNum == 0:
                continue
            pos = self.serv_redis_db.zrank(key, org)
            if pos is None:
                continue
            trophy_rank = self.posToRankMapping(pos, totNum)
            trophy_Pnts = self.serv_redis_db.zscore(key, org)
            trophy.append({ 'categ': categ, 'trophy_points': trophy_Pnts, 'trophy_rank': trophy_rank, 'trophy_true_rank': trophy_rank, 'trophy_title': self.trophy_title[trophy_rank]})
        return trophy

    def getOrgsTrophyRanking(self, categ):
        keyname = '{mainKey}:{orgCateg}'
        res = self.serv_redis_db.zrange(keyname.format(mainKey=self.keyTrophy, orgCateg=categ), 0, -1, withscores=True, desc=True)
        res = [[org.decode('utf8'), score] for org, score in res]
        return res

    def getAllOrgsTrophyRanking(self):
        dico_categ = {}
        for categ in self.categories_in_trophy:
            res = self.getOrgsTrophyRanking(categ)
            dico_categ[categ] = res

    def posToRankMapping(self, pos, totNum):
        mapping = self.trophyMapping
        mapping_num = [math.ceil(float(float(totNum*i)/float(100))) for i in mapping]
        # print(pos, totNum)
        if pos == 0: #first
            position = 1
        else:
            temp_pos = pos
            counter = 1
            for num in mapping_num:
                if temp_pos < num:
                    position = counter
                else:
                    temp_pos -= num
                    counter += 1
        return self.trophyNum+1 - position

    def giveTrophyPointsToOrg(self, org, categ, points):
        keyname = '{mainKey}:{orgCateg}'
        self.serv_redis_db.zincrby(keyname.format(mainKey=self.keyTrophy, orgCateg=categ), org, points)

    def removeTrophyPointsFromOrg(self, org, categ, points):
        keyname = '{mainKey}:{orgCateg}'
        self.serv_redis_db.zincrby(keyname.format(mainKey=self.keyTrophy, orgCateg=categ), org, -points)

    ''' AWARDS HELPER '''
    def getLastAwardsFromRedis(self):
        date = datetime.datetime.now()
        keyname = self.keyLastAward
        prev_days = 7
        topNum = self.MAX_NUMBER_OF_LAST_CONTRIBUTOR # default Num
        addedOrg = []
        data = []
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            last_awards = getZrange(self.serv_redis_db, keyname, curDate, topNum)
            for dico_award, sec in last_awards:
                dico_award = json.loads(dico_award)
                org = dico_award['org']
                dic = {}
                dic['orgRank'] = self.getOrgContributionRank(org)['final_rank']
                dic['logo_path'] = self.getOrgLogoFromMISP(org)
                dic['org'] = org
                dic['epoch'] = sec
                dic['award'] = dico_award['award']
                data.append(dic)
        return data

    ''' MONTHLY CONTRIBUTION '''
    def getOrgPntFromRedis(self, org, date):
        scoreSum = 0
        for curDate in util.getMonthSpan(date):
            date_str = util.getDateStrFormat(curDate)
            keyname = "{}:{}".format(self.keyDay, date_str)
            data = self.serv_redis_db.zscore(keyname, org)
            if data is None:
                data = 0
            scoreSum += data
        return scoreSum

    def getOrgRankFromRedis(self, org, date):
        ptns = self.getOrgPntFromRedis(org, date)
        return self.getTrueRank(ptns)


    def getLastContributorsFromRedis(self):
        date = datetime.datetime.now()
        prev_days = 7
        topNum = self.MAX_NUMBER_OF_LAST_CONTRIBUTOR # default Num
        addedOrg = []
        data = []
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            last_contrib_org = getZrange(self.serv_redis_db, self.keyLastContrib, curDate, topNum)
            for org, sec in last_contrib_org:
                if org in addedOrg:
                    continue
                dic = {}
                dic['rank'] = self.getOrgRankFromRedis(org, date)
                dic['orgRank'] = self.getOrgContributionRank(org)['final_rank']
                dic['honorBadge'] =  self.getOrgHonorBadges(org)
                dic['logo_path'] = self.getOrgLogoFromMISP(org)
                dic['org'] = org
                dic['pnts'] = self.getOrgPntFromRedis(org, date)
                dic['epoch'] = sec
                data.append(dic)
                addedOrg.append(org)
        return data


    def getContributorFromRedis(self, org):
        date = datetime.datetime.now()
        epoch = self.serv_redis_db.zscore(self.keyLastContrib, org)
        dic = {}
        dic['rank'] = self.getOrgRankFromRedis(org, date)
        dic['orgRank'] = self.getOrgContributionRank(org)['final_rank']
        dic['honorBadge'] = self.getOrgHonorBadges(org)
        dic['logo_path'] = self.getOrgLogoFromMISP(org)
        dic['org'] = org
        dic['pnts'] = self.getOrgPntFromRedis(org, date)
        dic['epoch'] = epoch
        return dic

    def getTopContributorFromRedis(self, date):
        orgDicoPnts = {}
        for curDate in util.getMonthSpan(date):
            topNum = 0 # all
            contrib_org = getZrange(self.serv_redis_db, self.keyDay, curDate, topNum)
            for org, pnts in contrib_org:
                if org not in orgDicoPnts:
                    orgDicoPnts[org] = 0
                orgDicoPnts[org] += pnts

        data = []
        for org, pnts in orgDicoPnts.items():
            dic = {}
            dic['rank'] = self.getTrueRank(pnts)
            dic['orgRank'] = self.getOrgContributionRank(org)['final_rank']
            dic['honorBadge'] = self.getOrgHonorBadges(org)
            dic['logo_path'] = self.getOrgLogoFromMISP(org)
            dic['org'] = org
            dic['pnts'] = pnts
            data.append(dic)
        data.sort(key=lambda x: x['pnts'], reverse=True)

        return data

    def getTop5OvertimeFromRedis(self):
        data = []
        today = datetime.datetime.now()
        topSortedOrg = self.getTopContributorFromRedis(today) #Get current top
        # show current top 5 org points overtime (last 5 days)
        for dic in topSortedOrg[0:5]:
            org = dic['org']
            to_append = self.getOrgOvertime(org)
            data.append(to_append)
        return data

    def getOrgOvertime(self, org):
        overtime = []
        today = datetime.datetime.today()
        today = today.replace(hour=0, minute=0, second=0, microsecond=0)
        for curDate in util.getXPrevDaysSpan(today, 7):
            timestamp = util.getTimestamp(curDate)
            keyname = "{}:{}".format(self.keyDay, util.getDateStrFormat(curDate))
            org_score =  self.serv_redis_db.zscore(keyname, org)
            if org_score is None:
                org_score = 0
            overtime.append([timestamp, org_score])
        to_return = {'label': org, 'data': overtime}
        return to_return

    def getCategPerContribFromRedis(self, date):
        topNum = 0 # all
        contrib_org = self.getTopContributorFromRedis(date)
        for dic in contrib_org:
            org = dic['org']
            for categ in self.categories_in_datatable:
                    categ_score = 0
                    for curDate in util.getMonthSpan(date):
                        keyname = "{}:{}:{}".format(self.keyCateg, util.getDateStrFormat(curDate), categ)
                        temp = self.serv_redis_db.zscore(keyname, org)
                        if temp is None:
                            temp = 0
                        categ_score += temp
                    dic[categ] = categ_score
        return contrib_org


    def getAllOrgFromRedis(self):
        data = self.serv_redis_db.smembers(self.keyAllOrg)
        data = [x.decode('utf8') for x in data]
        return data

    def getCurrentOrgRankFromRedis(self, org):
        date = datetime.datetime.now()
        points = self.getOrgPntFromRedis(org, date)
        remainingPts = self.getRemainingPoints(points)
        data = {
            'org': org,
            'points': points,
            'rank': self.getRankLevel(points),
            'orgRank': self.getOrgContributionRank(org)['final_rank'],
            'honorBadge': self.getOrgHonorBadges(org),
            'remainingPts': remainingPts['remainingPts'],
            'stepPts': remainingPts['stepPts'],
        }
        return data

    def getRankLevel(self, points):
        if points == 0:
            return 0
        elif points == 1:
            return 1
        else:
            return float("{:.2f}".format(math.log(points, self.rankMultiplier)))

    def getTrueRank(self, ptns):
        return int(self.getRankLevel(ptns))

    def getRemainingPoints(self, points):
        prev = 0
        for i in [math.floor(self.rankMultiplier**x) for x in range(1,self.levelMax+1)]:
            if prev <= points < i:
                return { 'remainingPts': i-points, 'stepPts': prev }
            prev = i
        return { 'remainingPts': 0, 'stepPts': self.rankMultiplier**self.levelMax }

