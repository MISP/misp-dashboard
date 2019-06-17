#!/usr/bin/env python3

import argparse
import configparser
import copy
import datetime
import json
import logging
import os
import random
import sys
import time

import redis
import zmq

import util
from helpers import (contributor_helper, geo_helper, live_helper,
                     trendings_helper, users_helper)

configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

logDir = cfg.get('Log', 'directory')
logfilename = cfg.get('Log', 'dispatcher_filename')
logPath = os.path.join(logDir, logfilename)
if not os.path.exists(logDir):
    os.makedirs(logDir)
try:
    logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
except PermissionError as error:
    print(error)
    print("Please fix the above and try again.")
    sys.exit(126)
logger = logging.getLogger('zmq_dispatcher')

LISTNAME = cfg.get('RedisLIST', 'listName')

serv_log = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLog', 'db'))
serv_redis_db = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisDB', 'db'))
serv_list = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLIST', 'db'))

live_helper = live_helper.Live_helper(serv_redis_db, cfg)
geo_helper = geo_helper.Geo_helper(serv_redis_db, cfg)
contributor_helper = contributor_helper.Contributor_helper(serv_redis_db, cfg)
users_helper = users_helper.Users_helper(serv_redis_db, cfg)
trendings_helper = trendings_helper.Trendings_helper(serv_redis_db, cfg)


##############
## HANDLERS ##
##############

def handler_skip(zmq_name, jsonevent):
    logger.info('Log not processed')
    return

def handler_audit(zmq_name, jsondata):
    action = jsondata.get('action', None)
    jsonlog = jsondata.get('Log', None)

    if action is None or jsonlog is None:
        return

    # consider login operations
    if action == 'log': # audit is related to log
        logAction = jsonlog.get('action', None)
        if logAction == 'login': # only consider user login
            timestamp = int(time.time())
            email = jsonlog.get('email', '')
            org = jsonlog.get('org', '')
            users_helper.add_user_login(timestamp, org, email)
    else:
        pass

def handler_dispatcher(zmq_name, jsonObj):
    if "Event" in jsonObj:
        handler_event(zmq_name, jsonObj)

def handler_keepalive(zmq_name, jsonevent):
    logger.info('Handling keepalive')
    to_push = [ jsonevent['uptime'] ]
    live_helper.publish_log(zmq_name, 'Keepalive', to_push)

# Login are no longer pushed by `misp_json_user`, but by `misp_json_audit`
def handler_user(zmq_name, jsondata):
    logger.info('Handling user')
    action = jsondata['action']
    json_user = jsondata['User']
    json_org = jsondata['Organisation']
    org = json_org['name']
    if action == 'edit': #only consider user login
        pass
    else:
        pass

def handler_conversation(zmq_name, jsonevent):
    logger.info('Handling conversation')
    try: #only consider POST, not THREAD
        jsonpost = jsonevent['Post']
    except KeyError as e:
        logger.error('Error in handler_conversation: {}'.format(e))
        return
    org = jsonpost['org_name']
    categ = None
    action = 'add'
    eventName = 'no name or id yet...'
    contributor_helper.handleContribution(zmq_name, org,
                    'Discussion',
                    None,
                    action,
                    isLabeled=False)
    # add Discussion
    nowSec = int(time.time())
    trendings_helper.addTrendingDisc(eventName, nowSec)

def handler_object(zmq_name, jsondata):
    logger.info('Handling object')
    # check if jsonattr is an mispObject object
    if 'Object' in jsondata:
        jsonobj = jsondata['Object']
        soleObject = copy.deepcopy(jsonobj)
        del soleObject['Attribute']
        for jsonattr in jsonobj['Attribute']:
            jsonattrcpy = copy.deepcopy(jsonobj)
            jsonattrcpy['Event'] = jsondata['Event']
            jsonattrcpy['Attribute'] = jsonattr
            handler_attribute(zmq_name, jsonattrcpy, False, parentObject=soleObject)

def handler_sighting(zmq_name, jsondata):
    logger.info('Handling sighting')
    jsonsight = jsondata['Sighting']
    org = jsonsight['Event']['Orgc']['name']
    categ = jsonsight['Attribute']['category']
    action = jsondata.get('action', None)
    contributor_helper.handleContribution(zmq_name, org, 'Sighting', categ, action, pntMultiplier=2)
    handler_attribute(zmq_name, jsonsight, hasAlreadyBeenContributed=True)

    timestamp = jsonsight.get('date_sighting', None)

    if jsonsight['type'] == "0": # sightings
        trendings_helper.addSightings(timestamp)
    elif jsonsight['type'] == "1": # false positive
        trendings_helper.addFalsePositive(timestamp)

def handler_event(zmq_name, jsonobj):
    logger.info('Handling event')
    #fields: threat_level_id, id, info
    jsonevent = jsonobj['Event']

    #Add trending
    eventName = jsonevent['info']
    timestamp = jsonevent['timestamp']
    trendings_helper.addTrendingEvent(eventName, timestamp)
    tags = []
    for tag in jsonevent.get('Tag', []):
        tags.append(tag)
    trendings_helper.addTrendingTags(tags, timestamp)

    #redirect to handler_attribute
    if 'Attribute' in jsonevent:
        attributes = jsonevent['Attribute']
        if type(attributes) is list:
            for attr in attributes:
                jsoncopy = copy.deepcopy(jsonobj)
                jsoncopy['Attribute'] = attr
                handler_attribute(zmq_name, jsoncopy)
        else:
            handler_attribute(zmq_name, attributes)

    if 'Object' in jsonevent:
        objects = jsonevent['Object']
        if type(objects) is list:
            for obj in objects:
                jsoncopy = copy.deepcopy(jsonobj)
                jsoncopy['Object'] = obj
                handler_object(zmq_name, jsoncopy)
        else:
            handler_object(zmq_name, objects)

    action = jsonobj.get('action', None)
    eventLabeled = len(jsonobj.get('EventTag', [])) > 0
    org = jsonobj.get('Orgc', {}).get('name', None)

    if org is not None:
        contributor_helper.handleContribution(zmq_name, org,
                        'Event',
                        None,
                        action,
                        isLabeled=eventLabeled)

def handler_attribute(zmq_name, jsonobj, hasAlreadyBeenContributed=False, parentObject=False):
    logger.info('Handling attribute')
    # check if jsonattr is an attribute object
    if 'Attribute' in jsonobj:
        jsonattr = jsonobj['Attribute']
    else:
        jsonattr = jsonobj

    attributeType = 'Attribute' if jsonattr['object_id'] == '0' else 'ObjectAttribute'

    #Add trending
    categName = jsonattr['category']
    timestamp = jsonattr.get('timestamp', int(time.time()))
    trendings_helper.addTrendingCateg(categName, timestamp)
    tags = []
    for tag in jsonattr.get('Tag', []):
        tags.append(tag)
    trendings_helper.addTrendingTags(tags, timestamp)


    #try to get coord from ip
    if jsonattr['category'] == "Network activity":
        geo_helper.getCoordFromIpAndPublish(jsonattr['value'], jsonattr['category'])

    #try to get coord from ip
    if jsonattr['type'] == "phone-number":
        geo_helper.getCoordFromPhoneAndPublish(jsonattr['value'], jsonattr['category'])

    if not hasAlreadyBeenContributed:
        eventLabeled = len(jsonobj.get('EventTag', [])) > 0
        action = jsonobj.get('action', None)
        contributor_helper.handleContribution(zmq_name, jsonobj['Event']['Orgc']['name'],
                            attributeType,
                            jsonattr['category'],
                            action,
                            isLabeled=eventLabeled)
    # Push to log
    live_helper.publish_log(zmq_name, attributeType, jsonobj)

def handler_diagnostic_tool(zmq_name, jsonobj):
    res = time.time() - float(jsonobj['content'])
    serv_list.set('diagnostic_tool_response', str(res))

###############
## MAIN LOOP ##
###############

def process_log(zmq_name, event):
    topic, eventdata = event.split(' ', maxsplit=1)
    jsonevent = json.loads(eventdata)
    try:
        dico_action[topic](zmq_name, jsonevent)
    except KeyError as e:
        logger.error(e)


def main(sleeptime):
    numMsg = 0
    while True:
        content = serv_list.rpop(LISTNAME)
        if content is None:
            logger.info('Processed {} message(s) since last sleep.'.format(numMsg))
            numMsg = 0
            time.sleep(sleeptime)
            continue
        content = content.decode('utf8')
        the_json = json.loads(content)
        zmqName = the_json['zmq_name']
        content = the_json['content']
        process_log(zmqName, content)
        numMsg += 1


dico_action = {
        "misp_json":                handler_dispatcher,
        "misp_json_event":          handler_event,
        "misp_json_self":           handler_keepalive,
        "misp_json_attribute":      handler_attribute,
        "misp_json_object":         handler_object,
        "misp_json_sighting":       handler_sighting,
        "misp_json_organisation":   handler_skip,
        "misp_json_user":           handler_user,
        "misp_json_conversation":   handler_conversation,
        "misp_json_object_reference": handler_skip,
        "misp_json_audit": handler_audit,
        "diagnostic_channel":       handler_diagnostic_tool
        }


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='The ZMQ dispatcher. It pops from the redis buffer then redispatch it to the correct handlers')
    parser.add_argument('-s', '--sleep', required=False, dest='sleeptime', type=int, help='The number of second to wait before checking redis list size', default=5)
    args = parser.parse_args()

    try:
        main(args.sleeptime)
    except (redis.exceptions.ResponseError, KeyboardInterrupt) as error:
        print(error)
