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

import util
import geo_helper
import contributor_helper
import users_helper
import trendings_helper

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

geo_helper = geo_helper.Geo_helper(serv_redis_db, cfg)
contributor_helper = contributor_helper.Contributor_helper(serv_redis_db, cfg)
users_helper = users_helper.Users_helper(serv_redis_db, cfg)
trendings_helper = trendings_helper.Trendings_helper(serv_redis_db, cfg)

subscriber_log = redis_server_log.pubsub(ignore_subscribe_messages=True)
subscriber_log.psubscribe(cfg.get('RedisLog', 'channel'))
subscriber_map = redis_server_map.pubsub(ignore_subscribe_messages=True)
subscriber_map.psubscribe(cfg.get('RedisMap', 'channelDisp'))
subscriber_lastContrib = redis_server_log.pubsub(ignore_subscribe_messages=True)
subscriber_lastContrib.psubscribe(cfg.get('RedisLog', 'channelLastContributor'))
subscriber_lastAwards = redis_server_log.pubsub(ignore_subscribe_messages=True)
subscriber_lastAwards.psubscribe(cfg.get('RedisLog', 'channelLastAwards'))

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

''' GENERAL '''
def getZrange(keyCateg, date, topNum, endSubkey=""):
    date_str = util.getDateStrFormat(date)
    keyname = "{}:{}{}".format(keyCateg, date_str, endSubkey)
    data = serv_redis_db.zrange(keyname, 0, topNum-1, desc=True, withscores=True)
    data = [ [record[0].decode('utf8'), record[1]] for record in data ]
    return data

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
    categ_list = contributor_helper.categories_in_datatable
    categ_list_str = [ s[0].upper() + s[1:].replace('_', ' ') for s in categ_list]
    categ_list_points = [contributor_helper.DICO_PNTS_REWARD[categ] for categ in categ_list]

    org_rank = contributor_helper.org_rank
    org_rank_requirement_pnts = contributor_helper.org_rank_requirement_pnts
    org_rank_requirement_text = contributor_helper.org_rank_requirement_text
    org_rank_list = [[rank, title, org_rank_requirement_pnts[rank], org_rank_requirement_text[rank]] for rank, title in org_rank.items()]
    org_rank_list.sort(key=lambda x: x[0])
    org_rank_additional_text = contributor_helper.org_rank_additional_info

    org_honor_badge_title = contributor_helper.org_honor_badge_title
    org_honor_badge_title_list = [ [num, text] for num, text in contributor_helper.org_honor_badge_title.items()]
    org_honor_badge_title_list.sort(key=lambda x: x[0])

    trophy_categ_list = contributor_helper.categories_in_trophy
    trophy_categ_list_str = [ s[0].upper() + s[1:].replace('_', ' ') for s in trophy_categ_list]
    trophy_title = contributor_helper.trophy_title
    trophy_title_str = []
    for i in range(contributor_helper.trophyNum+1):
        trophy_title_str.append(trophy_title[i])
    trophy_mapping = ["Top 1"] + [ str(x)+"%" for x in contributor_helper.trophyMapping] + [" "]
    trophy_mapping.reverse()

    currOrg = request.args.get('org')
    if currOrg is None:
        currOrg = ""
    return render_template('contrib.html',
            currOrg=currOrg,
            rankMultiplier=contributor_helper.rankMultiplier,
            default_pnts_per_contribution=contributor_helper.default_pnts_per_contribution,
            additional_help_text=json.loads(cfg.get('CONTRIB', 'additional_help_text')),
            categ_list=json.dumps(categ_list),
            categ_list_str=categ_list_str,
            categ_list_points=categ_list_points,
            org_rank_json=json.dumps(org_rank),
            org_rank_list=org_rank_list,
            org_rank_additional_text=org_rank_additional_text,
            org_honor_badge_title=json.dumps(org_honor_badge_title),
            org_honor_badge_title_list=org_honor_badge_title_list,
            trophy_categ_list=json.dumps(trophy_categ_list),
            trophy_categ_list_id=trophy_categ_list,
            trophy_categ_list_str=trophy_categ_list_str,
            trophy_title=json.dumps(trophy_title),
            trophy_title_str=trophy_title_str,
            trophy_mapping=trophy_mapping,
            min_between_reload=cfg.getint('CONTRIB', 'min_between_reload')
            )

@app.route("/users")
def users():
    return render_template('users.html',
            )


@app.route("/trendings")
def trendings():
    maxNum = request.args.get('maxNum')
    try:
        maxNum = int(maxNum)
    except:
        maxNum = 15

    return render_template('trendings.html',
            maxNum=maxNum
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
    data = geo_helper.getTopCoord(date)
    return jsonify(data)

@app.route("/_getHitMap")
def getHitMap():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()
    data = geo_helper.getHitMap(date)
    return jsonify(data)

@app.route("/_getCoordsByRadius")
def getCoordsByRadius():
    try:
        dateStart = datetime.datetime.fromtimestamp(float(request.args.get('dateStart')))
        dateEnd = datetime.datetime.fromtimestamp(float(request.args.get('dateEnd')))
        centerLat = request.args.get('centerLat')
        centerLon = request.args.get('centerLon')
        radius = int(math.ceil(float(request.args.get('radius'))))
    except:
        return jsonify([])

    data = geo_helper.getCoordsByRadius(dateStart, dateEnd, centerLat, centerLon, radius)
    return jsonify(data)

''' CONTRIB '''

@app.route("/_getLastContributors")
def getLastContributors():
    return jsonify(contributor_helper.getLastContributorsFromRedis())

@app.route("/_eventStreamLastContributor")
def getLastContributor():
    return Response(eventStreamLastContributor(), mimetype="text/event-stream")

@app.route("/_eventStreamAwards")
def getLastStreamAwards():
    return Response(eventStreamAwards(), mimetype="text/event-stream")

def eventStreamLastContributor():
    for msg in subscriber_lastContrib.listen():
        content = msg['data'].decode('utf8')
        contentJson = json.loads(content)
        lastContribJson = json.loads(contentJson['log'])
        org = lastContribJson['org']
        to_return = contributor_helper.getContributorFromRedis(org)
        epoch = lastContribJson['epoch']
        to_return['epoch'] = epoch
        yield 'data: {}\n\n'.format(json.dumps(to_return))

def eventStreamAwards():
    for msg in subscriber_lastAwards.listen():
        content = msg['data'].decode('utf8')
        contentJson = json.loads(content)
        lastAwardJson = json.loads(contentJson['log'])
        org = lastAwardJson['org']
        to_return = contributor_helper.getContributorFromRedis(org)
        epoch = lastAwardJson['epoch']
        to_return['epoch'] = epoch
        to_return['award'] = lastAwardJson['award']
        yield 'data: {}\n\n'.format(json.dumps(to_return))

@app.route("/_getTopContributor")
def getTopContributor(suppliedDate=None):
    if suppliedDate is None:
        try:
            date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
        except:
            date = datetime.datetime.now()
    else:
        date = suppliedDate

    data = contributor_helper.getTopContributorFromRedis(date)
    return jsonify(data)

@app.route("/_getFameContributor")
def getFameContributor():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        today = datetime.datetime.now()
        # get previous month
        date = (datetime.datetime(today.year, today.month, 1) - datetime.timedelta(days=1))
    return getTopContributor(suppliedDate=date)

@app.route("/_getFameQualContributor")
def getFameQualContributor():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        today = datetime.datetime.now()
        # get previous month
        date = (datetime.datetime(today.year, today.month, 1) - datetime.timedelta(days=1))
    return getTopContributor(suppliedDate=date)

@app.route("/_getTop5Overtime")
def getTop5Overtime():
    return jsonify(contributor_helper.getTop5OvertimeFromRedis())

@app.route("/_getOrgOvertime")
def getOrgOvertime():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getOrgOvertime(org))

@app.route("/_getCategPerContrib")
def getCategPerContrib():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    return jsonify(contributor_helper.getCategPerContribFromRedis(date))

@app.route("/_getLatestAwards")
def getLatestAwards():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    return jsonify(contributor_helper.getLastAwardsFromRedis())

@app.route("/_getAllOrg")
def getAllOrg():
    return jsonify(contributor_helper.getAllOrgFromRedis())

@app.route("/_getOrgRank")
def getOrgRank():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getCurrentOrgRankFromRedis(org))

@app.route("/_getContributionOrgStatus")
def getContributionOrgStatus():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getCurrentContributionStatus(org))

@app.route("/_getHonorBadges")
def getHonorBadges():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getOrgHonorBadges(org))

@app.route("/_getTrophies")
def getTrophies():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getOrgTrophies(org))


''' USERS '''

@app.route("/_getUserLogins")
def getUserLogins():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    data = users_helper.getUserLoginsForPunchCard(date)
    return jsonify(data)

@app.route("/_getUserLoginsOvertime")
def getUserLoginsOvertime():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    data = users_helper.getUserLoginsOvertime(date)
    return jsonify(data)

@app.route("/_getTopOrglogin")
def getTopOrglogin():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    data = users_helper.getTopOrglogin(date, maxNum=12)
    return jsonify(data)

@app.route("/_getLoginVSCOntribution")
def getLoginVSCOntribution():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    data = users_helper.getLoginVSCOntribution(date)
    return jsonify(data)

@app.route("/_getUserLoginsAndContribOvertime")
def getUserLoginsAndContribOvertime():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    data = users_helper.getUserLoginsAndContribOvertime(date)
    return jsonify(data)

''' TRENDINGS '''
@app.route("/_getTrendingEvents")
def getTrendingEvents():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()

    specificLabel = request.args.get('specificLabel')
    data = trendings_helper.getTrendingEvents(dateS, dateE, specificLabel)
    return jsonify(data)

@app.route("/_getTrendingCategs")
def getTrendingCategs():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()


    data = trendings_helper.getTrendingCategs(dateS, dateE)
    return jsonify(data)

@app.route("/_getTrendingTags")
def getTrendingTags():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()


    data = trendings_helper.getTrendingTags(dateS, dateE)
    return jsonify(data)

@app.route("/_getTrendingSightings")
def getTrendingSightings():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()

    data = trendings_helper.getTrendingSightings(dateS, dateE)
    return jsonify(data)

@app.route("/_getTrendingDisc")
def getTrendingDisc():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()


    data = trendings_helper.getTrendingDisc(dateS, dateE)
    return jsonify(data)

@app.route("/_getTypeaheadData")
def getTypeaheadData():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()

    data = trendings_helper.getTypeaheadData(dateS, dateE)
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='localhost', port=8001, threaded=True)
