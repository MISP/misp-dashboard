#!/usr/bin/env bash

set -e
set -x

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"

# Getting CWD where bash script resides
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASH_HOME=${DIR}

cd ${DASH_HOME}

if [ -e "${DIR}/DASHENV/bin/python" ]; then
    echo "dashboard virtualenv seems to exist, good"
    ENV_PY=${DIR}/DASHENV/bin/python
else
    echo "Please make sure you have a dashboard environment, au revoir"
    exit 1
fi

redis_dir="${DASH_HOME}/../redis/src/"
if [ ! -e "${redis_dir}" ]; then
    [ ! -f "`which redis-server`" ] && echo "Either ${DASH_HOME}/../redis/src/ does not exist or 'redis-server' is not installed/not on PATH. Please fix and run again." && exit 1
    redis_dir=""
fi

netstat -an |grep LISTEN |grep 6250 |grep -v tcp6 ; check_redis_port=$?

# Configure accordingly, remember: 0.0.0.0 exposes to every active IP interface, play safe and bind it to something you trust and know
export FLASK_APP=server.py
export FLASK_DEBUG=0
export FLASK_PORT=8001
export FLASK_HOST=127.0.0.1

conf_dir="${DASH_HOME}/config/"

screenName="Misp-Dashboard"

screen -dmS "$screenName"
sleep 0.1
if [ "${check_redis_port}" == "1" ]; then
    echo -e $GREEN"\t* Launching Redis servers"$DEFAULT
    screen -S "$screenName" -X screen -t "redis-server" bash -c $redis_dir'redis-server '$conf_dir'6250.conf && echo "Started Redis" ; read x'
else
    echo -e $RED"\t* NOT starting Redis server, made a very unrealiable check on port 6250, and something seems to be there… please double check if this is good!"$DEFAULT
fi

echo -e $GREEN"\t* Launching zmq subscriber"$DEFAULT
screen -S "$screenName" -X screen -t "zmq-subscriber" bash -c 'echo "Starting zmq-subscriber" ; ${ENV_PY} ${DIR}/zmq_subscriber.py; read x'

echo -e $GREEN"\t* Launching zmq dispatcher"$DEFAULT
screen -S "$screenName" -X screen -t "zmq-dispatcher" bash -c 'echo "Starting zmq-dispatcher"; ${ENV_PY} ${DIR}/zmq_dispatcher.py; read x'

echo -e $GREEN"\t* Launching flask server"$DEFAULT
screen -S "$screenName" -X screen -t "flask" bash -c 'echo "Starting Flask Server"; ${ENV_PY} ${DIR}/server.py; read x'
