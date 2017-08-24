#!/usr/bin/env python3.5
from flask import Flask, render_template, Response
import json
from time import time as now
from time import sleep

app = Flask(__name__)

FIELDNAME = {
        'time': 'Time', 
        'level': 'Level', 
        'source': 'Source', 
        'name': 'Name', 
        'message': 'Message'
        }

FIELDNAME_ORDER = [ 'time', 'level', 'source', 'name', 'message' ]

class LogRow():
    def __init__(self, feed='', time='', level='level', src='source', name='name', message='wonderful meesage'):
        # Parse feed message
        
        # Assign potential supplied values
        self.time = time if time != '' else now()
        self.level = level
        self.source = src
        self.name = name
        self.message = message

    def get_head_row(self):
        to_ret = []
        for fn in FIELDNAME_ORDER:
            to_ret.append(FIELDNAME[fn])
        return to_ret

    def get_row(self):
        to_ret = {}
        #Number to keep them sorted (jsonify sort keys)
        to_ret[1] = self.time
        to_ret[2] = self.level
        to_ret[3] = self.source
        to_ret[4] = self.name
        to_ret[5] = self.message
        return to_ret


class EventMessage():
    def __init__(self, msg):
        self.feed = None
        self.isLog = EventMessage.is_log(msg)

        #get type of message: log or feed, then create
        if self.isLog:
            self.feed = msg
            #FIXME do parser
            self.feed = LogRow(feed=msg).get_row()
        else:
            self.feed = {feed.name: feed.data}

    def is_log(msg):
        return True

    def to_json(self):
        if self.isLog:
            to_ret = { 'log': self.feed, 'chart': "" }
        else:
            to_ret = { 'log': "", 'chart': self.feed }
        return 'data: {}\n\n'.format(json.dumps(to_ret))

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/_logs")
def logs():
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/_get_log_head")
def getLogHead():
    return json.dumps(LogRow().get_head_row())

def event_stream():
    #for msg in pubsub:
    for i in range(3):
        msg = now()
        sleep(0.3)
        print('sending', EventMessage(msg).to_json())
        yield EventMessage(msg).to_json()


if __name__ == '__main__':
    app.run(host='localhost', port=8000, debug=True)
