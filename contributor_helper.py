import util
import math, random
import configparser
import json
import datetime

class Contributor_helper:
    def __init__(self, serv_redis_db, cfg):
        self.serv_redis_db = serv_redis_db
        self.cfg = cfg

        self.MAX_NUMBER_OF_LAST_CONTRIBUTOR = cfg.getint('CONTRIB', 'max_number_of_last_contributor')
        self.categories_in_datatable = json.loads(cfg.get('CONTRIB', 'categories_in_datatable'))
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

    def getZrange(self, keyCateg, date, topNum, endSubkey=""):
        date_str = util.getDateStrFormat(date)
        keyname = "{}:{}{}".format(keyCateg, date_str, endSubkey)
        data = self.serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
        data = [ [record[0].decode('utf8'), record[1]] for record in data ]
        return data

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

    def getOrgLogoFromRedis(self, org):
        return 'logo_'+org

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
                'logo_path': 'logo1',
                'org': 'CIRCL',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'logo_path': 'logo2',
                'org': 'CASES',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'logo_path': 'logo3',
                'org': 'SMILE',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'logo_path': 'logo4',
                'org': 'ORG4',
                'pnts': random.randint(1,2**self.levelMax)
            },
            {
                'rank': random.randint(1,self.levelMax),
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
                'logo_path': 'logo1',
                'org': 'CIRCL',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'logo_path': 'logo2',
                'org': 'CASES',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'logo_path': 'logo3',
                'org': 'SMILE',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'logo_path': 'logo4',
                'org': 'ORG4',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
            {
                'rank': random.randint(1,self.levelMax),
                'logo_path': 'logo5',
                'org': 'ORG5',
                'pnts': random.randint(1,2**self.levelMax),
                'epoch': time.time() - random.randint(0, 10000)
            },
        ]
        return data2*2

    def TEST_getAllOrgFromRedis(self):
        data2 = ['CIRCL', 'CASES', 'SMILE' ,'ORG4' ,'ORG5', 'SUPER HYPER LONG ORGINZATION NAME', 'Org3']
        return data2
