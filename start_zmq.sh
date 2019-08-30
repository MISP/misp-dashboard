#!/usr/bin/env bash
#set -x

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"

# Getting CWD where bash script resides
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASH_HOME="${DIR}"
SCREEN_NAME="Misp_Dashboard"

cd ${DASH_HOME}

if [ -e "${DIR}/DASHENV/bin/python" ]; then
    echo "dashboard virtualenv seems to exist, good"
    ENV_PY="${DIR}/DASHENV/bin/python"
else
    echo "Please make sure you have a dashboard environment, au revoir"
    exit 1
fi

PID_SCREEN=$(screen -ls | grep ${SCREEN_NAME} | cut -f2 | cut -d. -f1)
if [[ $PID_SCREEN ]]; then
    echo -e $RED"* A screen '$SCREEN_NAME' is already launched"$DEFAULT
    echo -e $GREEN"Killing $PID_SCREEN"$DEFAULT;
    kill $PID_SCREEN
else
    echo 'No screen detected'
fi

screen -dmS ${SCREEN_NAME}

ps auxw |grep zmq_subscriber.py |grep -v grep ; check_zmq_subscriber=$?
ps auxw |grep zmq_dispatcher.py |grep -v grep ; check_zmq_dispatcher=$?
sleep 0.1
if [ "${check_zmq_subscriber}" == "1" ]; then
    echo -e $GREEN"\t* Launching zmq subscribers"$DEFAULT
    screen -S "Misp_Dashboard" -X screen -t "zmq-subscribers" bash -c ${ENV_PY}' ./zmq_subscribers.py; read x'
else
    echo -e $RED"\t* NOT starting zmq subscribers, made a rather unrealiable ps -auxw | grep for zmq_subscriber.py, and something seems to be there… please double check if this is good!"$DEFAULT
fi

sleep 0.1
if [ "${check_zmq_dispatcher}" == "1" ]; then
    echo -e $GREEN"\t* Launching zmq dispatcher"$DEFAULT
    screen -S "Misp_Dashboard" -X screen -t "zmq-dispacher" bash -c ${ENV_PY}' ./zmq_dispatcher.py; read x'
else
    echo -e $RED"\t* NOT starting zmq dispatcher, made a rather unrealiable ps -auxw | grep for zmq_dispatcher.py, and something seems to be there… please double check if this is good!"$DEFAULT
fi