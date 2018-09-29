import os
import json
import random
import datetime, time
import logging


class Live_helper:
    def __init__(self, serv_live, cfg):
        self.serv_live = serv_live
        self.cfg = cfg
        self.maxCacheHistory = cfg.get('Dashboard', 'maxCacheHistory')
        # REDIS keys
        self.CHANNEL = cfg.get('RedisLog', 'channel')
        self.prefix_redis_key = "TEMP_CACHE_LIVE:"

        # logger
        logDir = cfg.get('Log', 'directory')
        logfilename = cfg.get('Log', 'filename')
        logPath = os.path.join(logDir, logfilename)
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def publish_log(self, zmq_name, name, content, channel=None):
        channel = channel if channel is not None else self.CHANNEL
        to_send = { 'name': name, 'log': json.dumps(content), 'zmqName': zmq_name }
        to_send_keep = { 'name': name, 'log': content, 'zmqName': zmq_name }
        j_to_send = json.dumps(to_send)
        j_to_send_keep = json.dumps(to_send_keep)
        self.serv_live.publish(channel, j_to_send)
        self.logger.debug('Published: {}'.format(j_to_send))
        if name != 'Keepalive':
            self.add_to_stream_log_cache(name, j_to_send_keep)


    def get_stream_log_cache(self, cacheKey):
        rKey = self.prefix_redis_key+cacheKey
        entries = self.serv_live.lrange(rKey, 0, -1)
        to_ret = []
        for entry in entries:
            jentry = json.loads(entry.decode('utf8'))
            to_ret.append(jentry)
        return to_ret
    

    def add_to_stream_log_cache(self, cacheKey, item):
        rKey = self.prefix_redis_key+cacheKey
        if type(item) != str:
            item = json.dumps(item)
        self.serv_live.lpush(rKey, item)
        r = random.randint(0, 8)
        if r == 0:
            self.serv_live.ltrim(rKey, 0, 100)
