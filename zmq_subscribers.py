#!/usr/bin/env python3

import time, datetime
import logging
import redis
import configparser
import argparse
import os
import subprocess
import sys
import json
import atexit
import signal
import shlex
import pty
import threading

configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)
logDir = cfg.get('Log', 'directory')
logfilename = cfg.get('Log', 'subscriber_filename')
logPath = os.path.join(logDir, logfilename)
if not os.path.exists(logDir):
    os.makedirs(logDir)
logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
logger = logging.getLogger('zmq_subscriber')

CHANNEL = cfg.get('RedisLog', 'channel')
LISTNAME = cfg.get('RedisLIST', 'listName')

serv_list = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLIST', 'db'))

children = []

def signal_handler(signal, frame):
    for child in children:
        # We don't resume as we are already attached
        cmd = "screen -p"+child+" -X {arg}"
        argsc = shlex.split(cmd.format(arg = "kill"))
        print("\n\033[1;31m [-] Terminating {child}\033[0;39m".format(child=child))
        logger.info('Terminate: {child}'.format(child=child))
        subprocess.call(argsc) # kill window
    sys.exit(0)

###############
## MAIN LOOP ##
###############

def main():
    print("\033[1;31m [+] I am the subscriber's master - kill me to kill'em'all \033[0;39m")
    # screen needs a shell and I an no fan of shell=True
    (master, slave) = pty.openpty()
    try:
        for item in json.loads(cfg.get('RedisGlobal', 'misp_instances')):
            name = shlex.quote(item.get("name"))
            zmq = shlex.quote(item.get("zmq"))
            print("\033[1;32m [+] Subscribing to "+zmq+"\033[0;39m")
            logger.info('Launching: {child}'.format(child=name))
            children.append(name)
            subprocess.Popen(["screen", "-r", "Misp_Dashboard", "-X", "screen", "-t", name ,sys.executable, "./zmq_subscriber.py", "-n", name, "-u", zmq], close_fds=True, shell=False, stdin=slave, stdout=slave, stderr=slave)
    except ValueError as error:
        print("\033[1;31m [!] Fatal exception: {error} \033[0;39m".format(error=error))
        logger.error("JSON error: %s", error)
        sys.exit(1)
    signal.signal(signal.SIGINT, signal_handler)
    forever = threading.Event()
    forever.wait()  # Wait for SIGINT

if __name__ == "__main__":
    main()
