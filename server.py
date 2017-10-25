#!/usr/bin/env python3.5
from flask import Flask, render_template, request, Response, jsonify
import json
import redis
import random
import configparser
from time import gmtime as now
from time import sleep, strftime
import datetime
import os

configfile = os.path.join(os.environ['VIRTUAL_ENV'], '../config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

app = Flask(__name__)

redis_server_log = redis.StrictRedis(
        host=cfg.get('RedisLog', 'host'),
        port=cfg.getint('RedisLog', 'port'),
        db=cfg.getint('RedisLog', 'db'))
redis_server_map = redis.StrictRedis(
        host=cfg.get('RedisMap', 'host'),
        port=cfg.getint('RedisMap', 'port'),
        db=cfg.getint('RedisMap', 'db'))
serv_redis_db = redis.StrictRedis(
        host=cfg.get('RedisDB', 'host'),
        port=cfg.getint('RedisDB', 'port'),
        db=cfg.getint('RedisDB', 'db'))

subscriber_log = redis_server_log.pubsub(ignore_subscribe_messages=True)
subscriber_log.psubscribe(cfg.get('RedisLog', 'channel'))
subscriber_map = redis_server_map.pubsub(ignore_subscribe_messages=True)
subscriber_map.psubscribe(cfg.get('RedisMap', 'channelDisp'))
eventNumber = 0

class LogItem():

    FIELDNAME_ORDER = []
    FIELDNAME_ORDER_HEADER = []
    FIELDNAME_ORDER.append("time")
    FIELDNAME_ORDER_HEADER.append("time")
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
            to_ret.append(fn[0].upper()+fn[1:])
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

def getZrange(keyCateg, wantedDate, topNum):
    aDateTime = datetime.datetime.now()

    date_str = str(aDateTime.year)+str(aDateTime.month)+str(aDateTime.day)
    keyname = "{}:{}".format(keyCateg, date_str)
    data = serv_redis_db.zrange(keyname, 0, 5, desc=True, withscores=True)
    return data


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
            graph_log_refresh_rate=cfg.getint('Dashboard' ,'graph_log_refresh_rate'),
            char_separator=cfg.get('Log', 'char_separator'),
            rotation_wait_time=cfg.getint('Dashboard' ,'rotation_wait_time'),
            max_img_rotation=cfg.getint('Dashboard' ,'max_img_rotation'),
            hours_spanned=cfg.getint('Dashboard' ,'hours_spanned'),
            zoomlevel=cfg.getint('Dashboard' ,'zoomlevel')
            )


@app.route("/geo")
def geo():
    return render_template('geo.html')

@app.route("/_getTopCoord")
def getTopCoord():
    try:
        dayNum = int(request.args.get('dayNum'))
    except:
        dayNum = 1
    keyCateg = "GEO_COORD"
    topNum = 6 # default Num
    data = getZrange(keyCateg, dayNum, topNum)
    data = [ [record[0].decode('utf8'), record[1]] for record in data ] 
    return jsonify(data)

@app.route("/_getHitMap")
def getHitMap():
    try:
        dayNum = int(request.args.get('dayNum'))
    except:
        dayNum = 1
    keyCateg = "GEO_COUNTRY"
    topNum = -1 # default Num
    data = getZrange(keyCateg, dayNum, topNum)
    return jsonify(data)

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

if __name__ == '__main__':
    app.run(host='localhost', port=8000, threaded=True)
