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
    def getOrgLogoFromRedis(self, org):
        return "{}/img/orgs/{}.png".format(self.misp_web_url, org)

    def getZrange(self, keyCateg, date, topNum, endSubkey=""):
        date_str = util.getDateStrFormat(date)
        keyname = "{}:{}{}".format(keyCateg, date_str, endSubkey)
        data = self.serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
        data = [ [record[0].decode('utf8'), record[1]] for record in data ]
        return data

    ''' CONTRIBUTION RANK '''
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
        num_of_previous_req_not_fulfilled = len([x for x in requirement_not_fulfilled if x<final_rank])
        final_rank = final_rank -  num_of_previous_req_not_fulfilled
        return [final_rank, requirement_fulfilled, requirement_not_fulfilled]

    def giveContribRankToOrg(self, org, rankNum):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        serv_redis_db.set(keyname.format(org=orgName, orgCateg='CONTRIB_REQ_'+str(rankNum)), 1)

    def removeContribRankFromOrg(self, org, rankNum):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        serv_redis_db.delete(keyname.format(org=orgName, orgCateg='CONTRIB_REQ_'+str(rankNum)))

    # 1 for fulfilled, 0 for not fulfilled, -1 for not relevant
    def getCurrentContributionStatus(self, org):
        final_rank, requirement_fulfilled, requirement_not_fulfilled = self.getOrgContributionRank(org)
        to_ret = {}
        for i in range(1, self.org_rank_maxLevel+1):
            if i in requirement_fulfilled:
                to_ret[i] = 1
            elif i in requirement_not_fulfilled and i<=final_rank:
                to_ret[i] = 0
            else:
                to_ret[i] = -1
        return to_ret

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
        serv_redis_db.set(keyname.format(org=orgName, orgCateg='BADGE_'+str(badgeNum)), 1)

    def removeBadgeFromOrg(self, org, badgeNum):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        serv_redis_db.delete(keyname.format(org=orgName, orgCateg='BADGE_'+str(badgeNum)))

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
        topNum = self.MAX_NUMBER_OF_LAST_CONTRIBUTOR # default Num
        last_contrib_org = self.getZrange(keyname, date, topNum)
        data = []
        for org, sec in last_contrib_org:
            dic = {}
            dic['rank'] = self.getOrgRankFromRedis(org, date)
            dic['logo_path'] = self.getOrgLogoFromRedis(org)
            dic['org'] = org
            dic['pnts'] = self.getOrgPntFromRedis(org, date)
            dic['epoch'] = sec
            data.append(dic)
        return data

    def getContributorFromRedis(self, org):
        date = datetime.datetime.now()
        epoch = self.serv_redis_db.zscore("CONTRIB_LAST", org)
        dic = {}
        dic['rank'] = self.getOrgRankFromRedis(org, date)
        dic['logo_path'] = self.getOrgLogoFromRedis(org)
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
            dic['logo_path'] = self.getOrgLogoFromRedis(org)
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
            overtime = []
            for deltaD in  range(1,6,1):
                date = (datetime.datetime(today.year, today.month, today.day) - datetime.timedelta(days=deltaD))
                keyname = 'CONTRIB_DAY:'+util.getDateStrFormat(date)
                org_score =  self.serv_redis_db.zscore(keyname, org)
                if org_score is None:
                    org_score = 0
                overtime.append([deltaD, org_score])
            to_append = {'label': org, 'data': overtime}
            data.append(to_append)
        return data

    def getCategPerContribFromRedis(self, date):
        keyCateg = "CONTRIB_DAY"
        topNum = 0 # all
        contrib_org = self.getZrange(keyCateg, date, topNum)
        data = []
        for org, pnts in contrib_org:
            dic = {}
            dic['rank'] = self.getTrueRank(pnts)
            dic['logo_path'] = self.getOrgLogoFromRedis(org)
            dic['org'] = org
            dic['pnts'] = pnts
            for categ in self.categories_in_datatable:
                keyname = 'CONTRIB_CATEG:'+util.getDateStrFormat(date)+':'+categ
                categ_score = self.serv_redis_db.zscore(keyname, org)
                if categ_score is None:
                    categ_score = 0
                dic[categ] = categ_score
            data.append(dic)
        return data

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


    ''' TEST DATA '''

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
        data2 = [
            {'label': 'CIRCL', 'data': [[0, 4], [1, 7], [2,14]]},
            {'label': 'CASES', 'data': [[0, 1], [1, 5], [2,2]]}
        ]
        return data2

    def TEST_getTopContributorFromRedis(self, date):
        data2 = [
            {
                'rank': random.randint(1,self.levelMax),
                'orgRank': random.randint(1,self.levelMax),
                'honorBadge': [1,2],
                'logo_path': self.getOrgLogoFromRedis('MISP'),
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
                'logo_path': self.getOrgLogoFromRedis('MISP'),
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
        return {'rank': final_rank, 'status': to_ret}

    def TEST_getOrgHonorBadges(self, org):
        keyname = 'CONTRIB_ORG:{org}:{orgCateg}'
        honorBadge = []
        for i in range(1, self.honorBadgeNum+1):
            key = keyname.format(org=org, orgCateg='BADGE_'+str(i))
            if random.randint(0,1) == 1: #existing
                honorBadge.append(1)
            else:
                honorBadge.append(0)
        print(honorBadge)
        return honorBadge
