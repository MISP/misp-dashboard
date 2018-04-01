#!/bin/bash

set -e

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASH_HOME="${DIR}/.."

conf_dir="${DASH_HOME}/config/"
redis_dir="${DASH_HOME}/../redis/src/"
test_dir="${DASH_HOME}/tests/"
screenName="Misp-Dashboard-test"

screen -dmS "$screenName"
sleep 0.1
echo -e $GREEN"* Launching Redis servers"$DEFAULT
screen -S "$screenName" -X screen -t "redis-server" bash -c $redis_dir'redis-server --port 6260; read x'
