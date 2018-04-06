#!/usr/bin/env bash

set -x

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"

# Getting CWD where bash script resides
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASH_HOME="${DIR}"

cd ${DASH_HOME}

if [ -e "${DIR}/DASHENV/bin/python" ]; then
    echo "dashboard virtualenv seems to exist, good"
    ENV_PY="${DIR}/DASHENV/bin/python"
else
    echo "Please make sure you have a dashboard environment, au revoir"
    exit 1
fi

[ ! -f "`which redis-server`" ] && echo "'redis-server' is not installed/not on PATH. Please fix and run again." && exit 1

netstat -an |grep LISTEN |grep 6250 |grep -v tcp6 ; check_redis_port=$?
netstat -an |grep LISTEN |grep 8001 |grep -v tcp6 ; check_dashboard_port=$?
ps auxw |grep zmq_subscriber.py |grep -v grep ; check_zmq_subscriber=$?
ps auxw |grep zmq_dispatcher.py |grep -v grep ; check_zmq_dispatcher=$?

# Configure accordingly, remember: 0.0.0.0 exposes to every active IP interface, play safe and bind it to something you trust and know
export FLASK_APP=server.py
export FLASK_DEBUG=0
export FLASK_PORT=8001
export FLASK_HOST=127.0.0.1

conf_dir="config/"

sleep 0.1
if [ "${check_redis_port}" == "1" ]; then
    echo -e $GREEN"\t* Launching Redis servers"$DEFAULT
    redis-server ${conf_dir}6250.conf &
else
    echo -e $RED"\t* NOT starting Redis server, made a very unrealiable check on port 6250, and something seems to be there… please double check if this is good!"$DEFAULT
fi

sleep 0.1
if [ "${check_zmq_subscriber}" == "1" ]; then
    echo -e $GREEN"\t* Launching zmq subscriber"$DEFAULT
    ${ENV_PY} ./zmq_subscriber.py &
else
    echo -e $RED"\t* NOT starting zmq subscriber, made a rather unrealiable ps -auxw | grep for zmq_subscriber.py, and something seems to be there… please double check if this is good!"$DEFAULT
fi

sleep 0.1
if [ "${check_zmq_dispatcher}" == "1" ]; then
    echo -e $GREEN"\t* Launching zmq dispatcher"$DEFAULT
    ${ENV_PY} ./zmq_dispatcher.py &
else
    echo -e $RED"\t* NOT starting zmq dispatcher, made a rather unrealiable ps -auxw | grep for zmq_dispatcher.py, and something seems to be there… please double check if this is good!"$DEFAULT
fi

sleep 0.1
if [ "${check_dashboard_port}" == "1" ]; then
    echo -e $GREEN"\t* Launching flask server"$DEFAULT
    ${ENV_PY} ./server.py &
else
    echo -e $RED"\t* NOT starting flask server, made a very unrealiable check on port 8001, and something seems to be there… please double check if this is good!"$DEFAULT
fi
