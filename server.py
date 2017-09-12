#!/usr/bin/env python3.5
from flask import Flask, render_template, Response
import json
import redis
import configparser
from time import gmtime as now
from time import sleep, strftime
import os

configfile = os.path.join(os.environ['VIRTUAL_ENV'], '../config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

app = Flask(__name__)

redis_server = redis.StrictRedis(
        host=cfg.get('Redis', 'host'),
        port=cfg.getint('Redis', 'port'),
        db=cfg.getint('Redis', 'db'))

subscriber = redis_server.pubsub(ignore_subscribe_messages=True)
subscriber.psubscribe(cfg.get('Redis', 'channel'))
eventNumber = 0

class LogItem():

    FIELDNAME_ORDER = []
    for item in json.loads(cfg.get('Log', 'fieldname_order')):
        FIELDNAME_ORDER.append(item)

    #def __init__(self, feed='', time='', level='level', src='source', name='name', message='wonderful meesage'):
    def __init__(self, feed):
        self.time = strftime("%H:%M:%S", now())
        #FIXME Parse feed message?
        self.fields = []
        self.fields.append(self.time)
        for f in feed:
            self.fields.append(f)

    def get_head_row(self):
        to_ret = []
        for fn in LogItem.FIELDNAME_ORDER:
            to_ret.append(fn[0].upper()+fn[1:])
        return to_ret

    def get_row(self):
        to_ret = {}
        #Number to keep them sorted (jsonify sort keys)
        for i in range(len(LogItem.FIELDNAME_ORDER)):
            try:
                to_ret[i] = self.fields[i]
            except IndexError: # not enough field in rcv item
                to_ret[i] = ''
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
        self.feed = json.loads(jsonMsg['log'])
        self.feed = LogItem(self.feed).get_row()

    def to_json(self):
        to_ret = { 'log': self.feed, 'feedName': self.feedName }
        return 'data: {}\n\n'.format(json.dumps(to_ret))

@app.route("/")
def index():
    return render_template('index.html', 
            graph_log_refresh_rate=cfg.getint('Dashboard' ,'graph_log_refresh_rate')
            )

@app.route("/_logs")
def logs():
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/_get_log_head")
def getLogHead():
    return json.dumps(LogItem('').get_head_row())

def event_stream():
    for msg in subscriber.listen():
        content = msg['data']
        yield EventMessage(content).to_json()

if __name__ == '__main__':
    app.run(host='localhost', port=8000)
