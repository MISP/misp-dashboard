import util
import math, random
import os
import configparser
import json
import datetime

class Contributor_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.cfg = cfg
        self.cfg_org_rank = configparser.ConfigParser()
        self.cfg_org_rank.read(os.path.join(os.environ['DASH_CONFIG'], 'ranking.cfg'))

        #honorBadge
        self.honorBadgeNum = len(self.cfg_org_rank.options('HonorBadge'))
        self.heavilyCount = self.cfg_org_rank.getint('rankRequirementsMisc', 'heavilyCount')
        self.recentDays = self.cfg_org_rank.getint('rankRequirementsMisc', 'recentDays')
        self.regularlyDays = self.cfg_org_rank.getint('rankRequirementsMisc', 'regularlyDays')

        self.org_honor_badge_title = {}
        for badgeNum in range(1, self.honorBadgeNum+1): #get Num of honorBadge
            self.org_honor_badge_title[badgeNum] = self.cfg_org_rank.get('HonorBadge', str(badgeNum))

        self.trophyDifficulty = self.cfg_org_rank.getfloat('TrophyDifficulty', 'difficulty')
        self.trophyNum = len(self.cfg_org_rank.options('HonorTrophyCateg'))
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
        self.categories_in_datatable = json.loads(cfg.get('CONTRIB', 'categories_in_datatable'))

        #MONTHLY RANKING
        self.default_pnts_per_contribution = json.loads(cfg.get('CONTRIB', 'default_pnts_per_contribution'))
        temp = json.loads(cfg.get('CONTRIB', 'pnts_per_contribution'))
        self.DICO_PNTS_REWARD = {}
        for categ, pnts in temp:
            self.DICO_PNTS_REWARD[categ] = pnts
        # fill other categ with default points
        for categ in self.categories_in_datatable:
            if categ in self.DICO_PNTS_REWARD:
                continue
            else:
                self.DICO_PNTS_REWARD[categ] = self.default_pnts_per_contribution

        self.rankMultiplier = cfg.getfloat('CONTRIB' ,'rankMultiplier')
        self.levelMax = 16


    ''' HELPER '''
    def getOrgLogoFromMISP(self, org):
        return "{}/img/orgs/{}.png".format(self.misp_web_url, org)

    def getZrange(self, keyCateg, date, topNum, endSubkey=""):
        date_str = util.getDateStrFormat(date)
        keyname = "{}:{}{}".format(keyCateg, date_str, endSubkey)
        data = self.serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
        data = [ [record[0].decode('utf8'), record[1]] for record in data ]
        return data

    def addContributionToCateg(self, date, categ, org, count=1):
        today_str = util.getDateStrFormat(date)
        keyname = "CONTRIB_CATEG:{}:{}".format(today_str, categ)
        self.serv_redis_db.zincrby(keyname, org, count)

    ''' CONTRIBUTION RANK '''
    def getOrgContributionTotalPoints(self, org):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        pnts = self.serv_redis_db.get(keyname.format(org=org, orgCateg='points'))
        if pnts is None:
            pnts = 0
        else:
            pnts = int(pnts.decode('utf8'))
        return pnts

    # return: [final_rank, requirement_fulfilled, requirement_not_fulfilled]
    def getOrgContributionRank(self, org):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        final_rank = 0
        requirement_fulfilled = []
        requirement_not_fulfilled = []
        for i in range(1, self.org_rank_maxLevel+1):
            key = keyname.format(org=org, orgCateg='CONTRIB_REQ_'+str(i))
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
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        self.serv_redis_db.set(keyname.format(org=org, orgCateg='CONTRIB_REQ_'+str(rankNum)), 1)

    def removeContribRankFromOrg(self, org, rankNum):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        self.serv_redis_db.delete(keyname.format(org=org, orgCateg='CONTRIB_REQ_'+str(rankNum)))

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
    def updateOrgContributionRank(self, orgName, pnts_to_add, action, contribType, eventTime, isLabeled):
        ContributionStatus = chelper.getCurrentContributionStatus(org)
        oldRank = ContributionStatus['final_rank']
        oldContributionStatus = ContributionStatus['status']
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        # update total points
        totOrgPnts = self.serv_redis_db.incrby(keyname.format(org=orgName, orgCateg='points'), pnts_to_add)

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

        print([r for r, ttl in contrib])
        for rankReq, ttl in contrib:
            self.serv_redis_db.set(keyname.format(org=orgName, orgCateg='CONTRIB_REQ_'+str(rankReq)), 1)
            self.serv_redis_db.expire(keyname.format(org=orgName, orgCateg='CONTRIB_REQ_'+str(rankReq)), ttl)

        ContributionStatus = chelper.getCurrentContributionStatus(org)
        newRank = ContributionStatus['final_rank']
        newContributionStatus = ContributionStatus['status']
        awards_given = []
        if newRank > oldRank:
            awards_given.append(['rank', newRank])
        for i in range(len(oldContributionStatus)):
            if oldContributionStatus[i] != newContributionStatus[i]:
                awards_given.append(['contribution_status', i])

        print(awards_given)
        return awards_given

    ''' HONOR BADGES '''
    def getOrgHonorBadges(self, org):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        honorBadge = []
        for i in range(1, self.honorBadgeNum+1):
            key = keyname.format(org=org, orgCateg='BADGE_'+str(i))
            if self.serv_redis_db.get(key) is not None: #existing
                honorBadge.append(i)
        return honorBadge

    def giveBadgeToOrg(self, org, badgeNum):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        self.serv_redis_db.set(keyname.format(org=org, orgCateg='BADGE_'+str(badgeNum)), 1)

    def removeBadgeFromOrg(self, org, badgeNum):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        self.serv_redis_db.delete(keyname.format(org=org, orgCateg='BADGE_'+str(badgeNum)))

    ''' TROPHIES '''
    def getOrgTrophies(self, org):
        keyname = 'CONTRIB_TROPHY:{org}:{orgCateg}'
        trophy = []
        for categ in self.categories_in_trophy:
            key = keyname.format(org=org, orgCateg=categ)
            trophy_Pnts = self.serv_redis_db.get(key)
            if trophy_Pnts is not None: #existing
                trophy_Pnts = float(trophy_Pnts.decode('utf8'))
                trophy_rank = self.getRankTrophy(trophy_Pnts)
                trophy_true_rank = self.getTrueRankTrophy(trophy_Pnts)
                trophy.append({ 'categ': categ, 'trophy_points': trophy_Pnts, 'trophy_rank': trophy_rank, 'trophy_true_rank': trophy_true_rank, 'trophy_title': self.trophy_title[trophy_true_rank]})
        return trophy

    def giveTrophyPointsToOrg(self, org, categ, points):
        keyname = 'CONTRIB_TROPHY:{org}:{orgCateg}'
        self.serv_redis_db.incrby(keyname.format(org=org, orgCateg=categ), points)

    def removeTrophyPointsFromOrg(self, org, categ, points):
        keyname = 'CONTRIB_TROPHY:{org}:{orgCateg}'
        self.serv_redis_db.incrby(keyname.format(org=org, orgCateg=categ), -points)

    ''' AWARDS HELPER '''
    def getLastAwardsFromRedis(self):
        date = datetime.datetime.now()
        keyname = "CONTRIB_LAST_AWARDS"
        prev_days = 7
        topNum = self.MAX_NUMBER_OF_LAST_CONTRIBUTOR # default Num
        addedOrg = []
        data = []
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            last_awards = self.getZrange(keyname, curDate, topNum)
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
        keyCateg = 'CONTRIB_DAY'
        scoreSum = 0
        for curDate in util.getMonthSpan(date):
            date_str = util.getDateStrFormat(curDate)
            keyname = "{}:{}".format(keyCateg, date_str)
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
        keyname = "CONTRIB_LAST"
        prev_days = 7
        topNum = self.MAX_NUMBER_OF_LAST_CONTRIBUTOR # default Num
        addedOrg = []
        data = []
        for curDate in util.getXPrevDaysSpan(date, prev_days):
            last_contrib_org = self.getZrange(keyname, curDate, topNum)
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
        epoch = self.serv_redis_db.zscore("CONTRIB_LAST", org)
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
            keyCateg = "CONTRIB_DAY"
            topNum = 0 # all
            contrib_org = self.getZrange(keyCateg, curDate, topNum)
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
            keyname = 'CONTRIB_DAY:'+util.getDateStrFormat(curDate)
            org_score =  self.serv_redis_db.zscore(keyname, org)
            if org_score is None:
                org_score = 0
            overtime.append([timestamp, org_score])
        to_return = {'label': org, 'data': overtime}
        return to_return

    def getCategPerContribFromRedis(self, date):
        keyCateg = "CONTRIB_DAY"
        topNum = 0 # all
        contrib_org = self.getTopContributorFromRedis(date)
        for dic in contrib_org:
            org = dic['org']
            for categ in self.categories_in_datatable:
                    categ_score = 0
                    for curDate in util.getMonthSpan(date):
                        keyname = 'CONTRIB_CATEG:'+util.getDateStrFormat(curDate)+':'+categ
                        temp = self.serv_redis_db.zscore(keyname, org)
                        if temp is None:
                            temp = 0
                        categ_score += temp
                    dic[categ] = categ_score
        return contrib_org


    def getAllOrgFromRedis(self):
        data = self.serv_redis_db.smembers('CONTRIB_ALL_ORG')
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

    def getRankTrophy(self, points):
        if points == 0:
            return 0
        elif points == 1:
            return 1
        else:
            return float("{:.2f}".format(math.log(points, self.trophyDifficulty)))

    def getTrueRankTrophy(self, ptns):
        return int(self.getRankTrophy(ptns))

    '''           '''
    ''' TEST DATA '''
    '''           '''

    def TEST_getCategPerContribFromRedis(self, date):
        data2 = []
        for d in range(15):
            dic = {}
            dic['rank'] = random.randint(1,self.levelMax)
            dic['orgRank'] = random.randint(1,self.levelMax),
            dic['honorBadge'] = [random.randint(1,2)],
            dic['logo_path'] = 'logo'
            dic['org'] = 'Org'+str(d)
            dic['pnts'] = random.randint(1,2**self.levelMax)
            for f in self.categories_in_datatable:
                dic[f] = random.randint(0,1600)
            data2.append(dic)
        return data2

    def TEST_getTop5OvertimeFromRedis(self):
        import time
        now = time.time()
        data2 = [
            {'label': 'CIRCL', 'data': [[now, random.randint(1,50)], [now-util.ONE_DAY, random.randint(1,50)], [now-util.ONE_DAY*2, random.randint(1,50)], [now-util.ONE_DAY*3, random.randint(1,50)], [now-util.ONE_DAY*4, random.randint(1,50)]]},
            {'label': 'CASES', 'data': [[now, random.randint(1,50)], [now-util.ONE_DAY, random.randint(1,50)], [now-util.ONE_DAY*2, random.randint(1,50)], [now-util.ONE_DAY*3, random.randint(1,50)], [now-util.ONE_DAY*4, random.randint(1,50)]]},
            {'label': 'Org1', 'data': [[now, random.randint(1,50)], [now-util.ONE_DAY, random.randint(1,50)], [now-util.ONE_DAY*2, random.randint(1,50)], [now-util.ONE_DAY*3, random.randint(1,50)], [now-util.ONE_DAY*4, random.randint(1,50)]]},
            {'label': 'Org2', 'data': [[now, random.randint(1,50)], [now-util.ONE_DAY, random.randint(1,50)], [now-util.ONE_DAY*2, random.randint(1,50)], [now-util.ONE_DAY*3, random.randint(1,50)], [now-util.ONE_DAY*4, random.randint(1,50)]]},
            {'label': 'SMILE', 'data': [[now, random.randint(1,50)], [now-util.ONE_DAY, random.randint(1,50)], [now-util.ONE_DAY*2, random.randint(1,50)], [now-util.ONE_DAY*3, random.randint(1,50)], [now-util.ONE_DAY*4, random.randint(1,50)]]},
        ]
        return data2

    def TEST_getOrgOvertime(self, org):
        import time
        now = time.time()
        data = [
            {'label': org, 'data': [[now, random.randint(1,30)], [now-util.ONE_DAY, random.randint(1,30)], [now-util.ONE_DAY*2, random.randint(1,30)], [now-util.ONE_DAY*3, random.randint(1,30)], [now-util.ONE_DAY*4, random.randint(1,40)]]}
        ]
        return data

    def TEST_getTopContributorFromRedis(self, date):
        data2 = [
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [1,2],
                'logo_path': self.getOrgLogoFromMISP('MISP'),
                'org': 'MISP',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [1],
                'logo_path': 'logo1',
                'org': 'CIRCL',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [2],
                'logo_path': 'logo2',
                'org': 'CASES',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [],
                'logo_path': 'logo3',
                'org': 'SMILE',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [],
                'logo_path': 'logo4',
                'org': 'ORG4',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [],
                'logo_path': 'logo5',
                'org': 'ORG5',
                'pnts': random.randint(1,2**self.levelMax)
            },
        ]
        return data2*2

    def TEST_getLastContributorsFromRedis(self):
        import time
        data2 = [
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [1,2],
                'logo_path': self.getOrgLogoFromMISP('MISP'),
                'org': 'MISP',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [1],
                'logo_path': 'logo1',
                'org': 'CIRCL',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [2],
                'logo_path': 'logo2',
                'org': 'CASES',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [],
                'logo_path': 'logo3',
                'org': 'SMILE',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [],
                'logo_path': 'logo4',
                'org': 'ORG4',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [],
                'logo_path': 'logo5',
                'org': 'ORG5',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
        ]
        return data2*2

    def TEST_getAllOrgFromRedis(self):
        data2 = ['CIRCL', 'CASES', 'SMILE' ,'ORG4' ,'ORG5', 'SUPER HYPER LONG ORGINZATION NAME', 'Org3', 'MISP']
        return data2

    def TEST_getCurrentOrgRankFromRedis(self, org):
        date = datetime.datetime.now()
        points = random.randint(1,2**self.levelMax)
        remainingPts = self.getRemainingPoints(points)
        data = {
            'org': org,
            'points': points,
            'rank': self.getRankLevel(points),
            'remainingPts': remainingPts['remainingPts'],
            'stepPts': remainingPts['stepPts'],
        }
        return data

    def TEST_getCurrentContributionStatus(self, org):
        num = random.randint(1, self.org_rank_maxLevel)
        requirement_fulfilled = [x for x in range(1,num+1)]
        requirement_not_fulfilled = [x for x in range(num,self.org_rank_maxLevel+1-num)]

        num2 = random.randint(1, self.org_rank_maxLevel)
        if num2 < num-1:
            to_swap = requirement_fulfilled[num2]
            del requirement_fulfilled[num2]
            requirement_not_fulfilled = [to_swap] + requirement_not_fulfilled

        final_rank = len(requirement_fulfilled)
        to_ret = {}
        for i in range(1, self.org_rank_maxLevel+1):
            if i in requirement_fulfilled:
                to_ret[i] = 1
            elif i in requirement_not_fulfilled and i<=final_rank:
                to_ret[i] = 0
            else:
                to_ret[i] = -1
        return {'rank': final_rank, 'status': to_ret, 'totPoints': random.randint(2**final_rank, 2**self.org_rank_maxLevel*4)}

    def TEST_getOrgHonorBadges(self, org):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        honorBadge = []
        for i in range(1, self.honorBadgeNum+1):
            key = keyname.format(org=org, orgCateg='BADGE_'+str(i))
            if random.randint(0,1) == 1: #existing
                honorBadge.append(1)
            else:
                honorBadge.append(0)
        return honorBadge

    def TEST_getOrgTrophies(self, org):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        trophy = []
        for categ in self.categories_in_trophy:
            key = keyname.format(org=org, orgCateg='TROPHY_'+categ)
            trophy_Pnts = random.randint(0,10)
            trophy.append({'categName': categ, 'rank': trophy_Pnts})
        return trophy
