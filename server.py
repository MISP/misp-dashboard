#!/usr/bin/env python3.5
from flask import Flask, render_template, request, Response, jsonify
import json
import redis
import random, math
import configparser
from time import gmtime as now
from time import sleep, strftime
import datetime
import os

configfile = os.path.join(os.environ['DASH_CONFIG'], 'config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

app = Flask(__name__)

redis_server_log = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLog', 'db'))
redis_server_map = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisMap', 'db'))
serv_redis_db = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisDB', 'db'))

categories_in_datatable = json.loads(cfg.get('CONTRIB', 'categories_in_datatable'))
MAX_NUMBER_OF_LAST_CONTRIBUTOR = cfg.getint('CONTRIB', 'max_number_of_last_contributor')

subscriber_log = redis_server_log.pubsub(ignore_subscribe_messages=True)
subscriber_log.psubscribe(cfg.get('RedisLog', 'channel'))
subscriber_map = redis_server_map.pubsub(ignore_subscribe_messages=True)
subscriber_map.psubscribe(cfg.get('RedisMap', 'channelDisp'))
eventNumber = 0

##########
## UTIL ##
##########

''' INDEX '''
class LogItem():

    FIELDNAME_ORDER = []
    FIELDNAME_ORDER_HEADER = []
    FIELDNAME_ORDER.append("Time")
    FIELDNAME_ORDER_HEADER.append("Time")
    for item in json.loads(cfg.get('Log', 'fieldname_order')):
        if type(item) is list:
            FIELDNAME_ORDER_HEADER.append(" | ".join(item))
        else:
            FIELDNAME_ORDER_HEADER.append(item)
        FIELDNAME_ORDER.append(item)

    def __init__(self, feed):
        self.time = strftime("%H:%M:%S", now())
        #FIXME Parse feed message?
        self.fields = []
        self.fields.append(self.time)
        for f in feed:
            self.fields.append(f)

    def get_head_row(self):
        to_ret = []
        for fn in LogItem.FIELDNAME_ORDER_HEADER:
            to_ret.append(fn)
        return to_ret

    def get_row(self):
        to_ret = {}
        #Number to keep them sorted (jsonify sort keys)
        for item in range(len(LogItem.FIELDNAME_ORDER)):
            try:
                to_ret[item] = self.fields[item]
            except IndexError: # not enough field in rcv item
                to_ret[item] = ''
        return to_ret


class EventMessage():
    # Suppose the event message is a json with the format {name: 'feedName', log:'logData'}
    def __init__(self, msg):
        msg = msg.decode('utf8')
        try:
            jsonMsg = json.loads(msg)
        except json.JSONDecodeError:
            print('json decode error')
            jsonMsg = { 'name': "undefined" ,'log': json.loads(msg) }

        self.feedName = jsonMsg['name']
        self.zmqName = jsonMsg['zmqName']
        self.feed = json.loads(jsonMsg['log'])
        self.feed = LogItem(self.feed).get_row()

    def to_json(self):
        to_ret = { 'log': self.feed, 'feedName': self.feedName, 'zmqName': self.zmqName }
        return 'data: {}\n\n'.format(json.dumps(to_ret))

''' CONTRIB '''

# max lvl is 16
def getRankLevel(points):
    if points == 0:
        return 0
    elif points == 1:
        return 1
    else:
        return float("{:.2f}".format(math.log(points, cfg.getfloat('CONTRIB' ,'rankMultiplier'))))

def getTrueRank(ptns):
    return int(getRankLevel(ptns))

def getRemainingPoints(points):
    prev = 0
    for i in [math.floor(cfg.getfloat('CONTRIB' ,'rankMultiplier')**x) for x in range(1,17)]:
        if prev <= points < i:
            return { 'remainingPts': i-points, 'stepPts': prev }
        prev = i
    return { 'remainingPts': 0, 'stepPts': cfg.getfloat('CONTRIB' ,'rankMultiplier')**16 }


''' GENERAL '''
def getMonthSpan(date):
    ds = datetime.datetime(date.year, date.month, 1)
    dyear = 1 if ds.month+1 > 12 else 0
    dmonth = -12 if ds.month+1 > 12 else 0
    de = datetime.datetime(ds.year + dyear, ds.month+1 + dmonth, 1)

    delta = de - ds
    to_return = []
    for i in range(delta.days):
        to_return.append(ds + datetime.timedelta(days=i))
    return to_return

def getDateStrFormat(date):
    return str(date.year)+str(date.month).zfill(2)+str(date.day).zfill(2)

def getZrange(keyCateg, date, topNum, endSubkey=""):
    date_str = getDateStrFormat(date)
    keyname = "{}:{}{}".format(keyCateg, date_str, endSubkey)
    data = serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
    data = [ [record[0].decode('utf8'), record[1]] for record in data ]
    return data

def getOrgPntFromRedis(org, date):
    keyCateg = 'CONTRIB_DAY'
    scoreSum = 0
    for curDate in getMonthSpan(date):
        date_str = getDateStrFormat(curDate)
        keyname = "{}:{}".format(keyCateg, date_str)
        data = serv_redis_db.zscore(keyname, org)
        if data is None:
            data = 0
        scoreSum += data
    return scoreSum

def getOrgRankFromRedis(org, date):
    ptns = getOrgPntFromRedis(org, date)
    return getTrueRank(ptns)

def getOrgLogoFromRedis(org):
    return 'logo_'+org

def getTopContributor_fromRedis(date):
    data2 = [
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo1',
            'org': 'CIRCL',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo2',
            'org': 'CASES',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo3',
            'org': 'SMILE',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo4',
            'org': 'ORG4',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo5',
            'org': 'ORG5',
        },
    ]

    orgDicoPnts = {}
    for curDate in getMonthSpan(date):
        keyCateg = "CONTRIB_DAY"
        topNum = 0 # all
        contrib_org = getZrange(keyCateg, curDate, topNum)
        for org, pnts in contrib_org:
            if org not in orgDicoPnts:
                orgDicoPnts[org] = 0
            orgDicoPnts[org] += pnts

    data = []
    for org, pnts in orgDicoPnts.items():
        dic = {}
        dic['rank'] = getTrueRank(pnts)
        dic['logo_path'] = getOrgLogoFromRedis(org)
        dic['org'] = org
        dic['pnts'] = pnts
        data.append(dic)
    data.sort(key=lambda x: x['pnts'], reverse=True)

    return data
    #return data2

###########
## ROUTE ##
###########

''' MAIN ROUTE '''

@app.route("/")
def index():
    ratioCorrection = 88
    pannelSize = [
            "{:.0f}".format(cfg.getint('Dashboard' ,'size_openStreet_pannel_perc')/100*ratioCorrection),
            "{:.0f}".format((100-cfg.getint('Dashboard' ,'size_openStreet_pannel_perc'))/100*ratioCorrection),
            "{:.0f}".format(cfg.getint('Dashboard' ,'size_world_pannel_perc')/100*ratioCorrection),
            "{:.0f}".format((100-cfg.getint('Dashboard' ,'size_world_pannel_perc'))/100*ratioCorrection)
            ]
    return render_template('index.html',
            pannelSize=pannelSize,
            size_dashboard_width=[cfg.getint('Dashboard' ,'size_dashboard_left_width'), 12-cfg.getint('Dashboard', 'size_dashboard_left_width')],
            itemToPlot=cfg.get('Dashboard', 'item_to_plot'),
            graph_log_refresh_rate=cfg.getint('Dashboard' ,'graph_log_refresh_rate'),
            char_separator=cfg.get('Log', 'char_separator'),
            rotation_wait_time=cfg.getint('Dashboard' ,'rotation_wait_time'),
            max_img_rotation=cfg.getint('Dashboard' ,'max_img_rotation'),
            hours_spanned=cfg.getint('Dashboard' ,'hours_spanned'),
            zoomlevel=cfg.getint('Dashboard' ,'zoomlevel')
            )


@app.route("/geo")
def geo():
    return render_template('geo.html',
            zoomlevel=cfg.getint('GEO' ,'zoomlevel'),
            default_updateFrequency=cfg.getint('GEO' ,'updateFrequency')
            )

@app.route("/contrib")
def contrib():
    categ_list = categories_in_datatable
    categ_list_str = [ s[0].upper() + s[1:].replace('_', ' ') for s in categories_in_datatable]
    currOrg = request.args.get('org')
    if currOrg is None:
        currOrg = ""
    return render_template('contrib.html',
            currOrg=currOrg,
            rankMultiplier=cfg.getfloat('CONTRIB' ,'rankMultiplier'),
            categ_list=json.dumps(categ_list),
            categ_list_str=categ_list_str
            )

''' INDEX '''

@app.route("/_logs")
def logs():
    return Response(event_stream_log(), mimetype="text/event-stream")

@app.route("/_maps")
def maps():
    return Response(event_stream_maps(), mimetype="text/event-stream")

@app.route("/_get_log_head")
def getLogHead():
    return json.dumps(LogItem('').get_head_row())

def event_stream_log():
    for msg in subscriber_log.listen():
        content = msg['data']
        yield EventMessage(content).to_json()

def event_stream_maps():
    for msg in subscriber_map.listen():
        content = msg['data'].decode('utf8')
        yield 'data: {}\n\n'.format(content)

''' GEO '''

@app.route("/_getTopCoord")
def getTopCoord():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()
    keyCateg = "GEO_COORD"
    topNum = 6 # default Num
    data = getZrange(keyCateg, date, topNum)
    return jsonify(data)

@app.route("/_getHitMap")
def getHitMap():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()
    keyCateg = "GEO_COUNTRY"
    topNum = 0 # all
    data = getZrange(keyCateg, date, topNum)
    return jsonify(data)

def isCloseTo(coord1, coord2):
    clusterMeter = cfg.getfloat('GEO' ,'clusteringDistance')
    clusterThres = math.pow(10, len(str(abs(clusterMeter)))-7) #map meter to coord threshold (~ big approx)
    if abs(float(coord1[0]) - float(coord2[0])) <= clusterThres:
        if abs(float(coord1[1]) - float(coord2[1])) <= clusterThres:
            return True
    return False

@app.route("/_getCoordsByRadius")
def getCoordsByRadius():
    dico_coord = {}
    to_return = []
    try:
        dateStart = datetime.datetime.fromtimestamp(float(request.args.get('dateStart')))
        dateEnd = datetime.datetime.fromtimestamp(float(request.args.get('dateEnd')))
        centerLat = request.args.get('centerLat')
        centerLon = request.args.get('centerLon')
        radius = int(math.ceil(float(request.args.get('radius'))))
    except:
        return jsonify(to_return)

    delta = dateEnd - dateStart
    for i in range(delta.days+1):
        correctDatetime = dateStart + datetime.timedelta(days=i)
        date_str = getDateStrFormat(correctDatetime)
        keyCateg = 'GEO_RAD'
        keyname = "{}:{}".format(keyCateg, date_str)
        res = serv_redis_db.georadius(keyname, centerLon, centerLat, radius, unit='km', withcoord=True)

        #sum up really close coord
        for data, coord in res:
            flag_added = False
            coord = [coord[0], coord[1]]
            #list all coord
            for dicoCoordStr in dico_coord.keys():
                dicoCoord = json.loads(dicoCoordStr)
                #if curCoord close to coord
                if isCloseTo(dicoCoord, coord):
                    #add data to dico coord
                    dico_coord[dicoCoordStr].append(data)
                    flag_added = True
                    break
            # coord not in dic
            if not flag_added:
                dico_coord[str(coord)] = [data]

        for dicoCoord, array in dico_coord.items():
            dicoCoord = json.loads(dicoCoord)
            to_return.append([array, dicoCoord])

    return jsonify(to_return)

''' CONTRIB '''

@app.route("/_getLastContributor")
def getLastContributor():
    data2 = [
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo1',
            'org': 'CIRCL',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo2',
            'org': 'CASES',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo3',
            'org': 'SMILE',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo4',
            'org': 'ORG4',
        },
        {
            'rank': random.randint(1,16),
            'logo_path': 'logo5',
            'org': 'ORG5',
        },
    ]
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()
    keyCateg = "CONTRIB_LAST"
    topNum = MAX_NUMBER_OF_LAST_CONTRIBUTOR # default Num
    last_contrib_org = getZrange(keyCateg, date, topNum)
    data = []
    for org, sec in last_contrib_org:
        dic = {}
        dic['rank'] = getOrgRankFromRedis(org, datetime.datetime.now())
        dic['logo_path'] = getOrgLogoFromRedis(org)
        dic['org'] = org
        dic['pnts'] = getOrgPntFromRedis(org, date)
        data.append(dic)
    return jsonify(data)
    #return jsonify(data2*2)

@app.route("/_getTopContributor")
def getTopContributor(suppliedDate=None):
    if suppliedDate is None:
        try:
            date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
        except:
            date = datetime.datetime.now()
    else:
        date = suppliedDate

    data = getTopContributor_fromRedis(date)
    return jsonify(data)

@app.route("/_getFameContributor")
def getFameContributor():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        today = datetime.datetime.now()
        # get previous month
        date = (datetime.datetime(today.year, today.month, 1) - datetime.timedelta(days=1))
    return getTopContributor(date)


@app.route("/_getTop5Overtime")
def getTop5Overtime():
    data2 = [
        {'label': 'CIRCL', 'data': [[0, 4], [1, 7], [2,14]]},
        {'label': 'CASES', 'data': [[0, 1], [1, 5], [2,2]]}
    ]
    data = []
    today = datetime.datetime.now()
    topSortedOrg = getTopContributor_fromRedis(today) #Get current top
    # show current top 5 org points overtime (last 5 days)
    for dic in topSortedOrg[0:5]:
        org = dic['org']
        overtime = []
        for deltaD in  range(1,6,1):
            date = (datetime.datetime(today.year, today.month, today.day) - datetime.timedelta(days=deltaD))
            keyname = 'CONTRIB_DAY:'+getDateStrFormat(date)
            org_score =  serv_redis_db.zscore(keyname, org)
            if org_score is None:
                org_score = 0
            overtime.append([deltaD, org_score])
        to_append = {'label': org, 'data': overtime}
        data.append(to_append)
    return jsonify(data)
    #return jsonify(data2)

@app.route("/_getCategPerContrib")
def getCategPerContrib():

    data2 = []
    for d in range(15):
        dic = {}
        dic['rank'] = random.randint(1,16)
        dic['logo_path'] = 'logo'
        dic['org'] = 'Org'+str(d)
        for f in categories_in_datatable:
            dic[f] = random.randint(0,1600)
        data2.append(dic)

    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()
    keyCateg = "CONTRIB_DAY"
    topNum = 0 # all
    contrib_org = getZrange(keyCateg, date, topNum)
    data = []
    for org, pnts in contrib_org:
        dic = {}
        dic['rank'] = getTrueRank(pnts)
        dic['logo_path'] = getOrgLogoFromRedis(org)
        dic['org'] = org
        dic['pnts'] = pnts
        for categ in categories_in_datatable:
            keyname = 'CONTRIB_CATEG:'+getDateStrFormat(date)+':'+categ
            categ_score = serv_redis_db.zscore(keyname, org)
            if categ_score is None:
                categ_score = 0
            dic[categ] = categ_score
        data.append(dic)

    return jsonify(data)
    return jsonify(data2)

@app.route("/_getAllOrg")
def getAllOrg():
    data = serv_redis_db.smembers('CONTRIB_ALL_ORG')
    data = [x.decode('utf8') for x in data]
    data2 = ['CIRCL', 'CASES', 'SMILE' ,'ORG4' ,'ORG5', 'SUPER HYPER LONG ORGINZATION NAME', 'Org3']
    return jsonify(data)
    #return jsonify(data2)

@app.route("/_getOrgRank")
def getOrgRank():
    try:
        org = request.args.get('org')
    except:
        org = ''
    date = datetime.datetime.now()
    points = random.randint(1,math.floor(cfg.getfloat('CONTRIB' ,'rankMultiplier')**16))
    points = getOrgPntFromRedis(org, date)
    #FIXME put 0 if org has no points
    remainingPts = getRemainingPoints(points)
    data = {'org': org,
    'points': points,
    'rank': getRankLevel(points),
    'remainingPts': remainingPts['remainingPts'],
    'stepPts': remainingPts['stepPts'],
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='localhost', port=8001, threaded=True)
