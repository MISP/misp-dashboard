#!/usr/bin/env bash

#set -x

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

if [[ -f "/etc/redhat-release" ]]; then
  echo "You are running a RedHat flavour. Detecting scl potential..."
  if [[ -f "/usr/bin/scl" ]]; then
    echo "scl detected, checking for redis-server"
    SCL_REDIS=$(scl -l|grep rh-redis)
    if [[ ! -z $SCL_REDIS ]]; then
      echo "We detected: ${SCL_REDIS} acting accordingly"
      REDIS_RUN="/usr/bin/scl enable ${SCL_REDIS}"
    fi
  else
    echo "redis-server seems not to be install in scl, perhaps system-wide, testing."
    [ ! -f "`which redis-server`" ] && echo "'redis-server' is not installed/not on PATH. Please fix and run again." && exit 1
  fi
else
  [ ! -f "`which redis-server`" ] && echo "'redis-server' is not installed/not on PATH. Please fix and run again." && exit 1
fi

netstat -an |grep LISTEN |grep 6250 |grep -v tcp6 ; check_redis_port=$?
netstat -an |grep LISTEN |grep 8001 |grep -v tcp6 ; check_dashboard_port=$?

# Configure accordingly, remember: 0.0.0.0 exposes to every active IP interface, play safe and bind it to something you trust and know
export FLASK_APP=server.py
export FLASK_DEBUG=0
export FLASK_PORT=8001
export FLASK_HOST=127.0.0.1

conf_dir="config/"

sleep 0.1
if [ "${check_redis_port}" == "1" ]; then
  echo -e $GREEN"\t* Launching Redis servers"$DEFAULT
    if [[ ! -z $REDIS_RUN ]]; then
      $REDIS_RUN "redis-server ${conf_dir}6250.conf" &
    else
      redis-server ${conf_dir}6250.conf &
    fi
else
    echo -e $RED"\t* NOT starting Redis server, made a very unrealiable check on port 6250, and something seems to be there… please double check if this is good!"$DEFAULT
fi

sleep 0.1
if [ "${check_dashboard_port}" == "1" ]; then
    echo -e $GREEN"\t* Launching flask server"$DEFAULT
    ${ENV_PY} ./server.py &
else
    echo -e $RED"\t* NOT starting flask server, made a very unrealiable check on port 8001, and something seems to be there… please double check if this is good!"$DEFAULT
fi

sleep 0.1
sudo -u zmqs /bin/bash ${DIR}/start_zmq.sh &
