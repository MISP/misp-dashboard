#!/bin/bash

set -e

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"

[ -z "$DASH_HOME" ] && echo "Needs the env var DASHENV. Run the script from the virtual environment." && exit 1;

conf_dir="${DASH_HOME}/config/"
redis_dir="${DASH_HOME}/../redis/src/"
test_dir="${DASH_HOME}/tests/"
screenName="Misp-Dashboard-test"

screen -dmS "$screenName"
sleep 0.1
echo -e $GREEN"\t* Launching Redis servers"$DEFAULT
screen -S "$screenName" -X screen -t "redis-server" bash -c $redis_dir'redis-server --port 6260; read x'
