#!/bin/bash

set -e

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"

[ -z "$DASH_HOME" ] && echo "Needs the env var DASHENV. Run the script from the virtual environment." && exit 1;

conf_dir="${DASH_HOME}/config/"
redis_dir="${DASH_HOME}/../redis/src/"
redis_dir="../../redis/src/"
test_dir="${DASH_HOME}/tests/"
screenName="Misp-Dashboard-test"


bash -c $redis_dir'redis-cli -p 6260 shutdown'
screen -S $screenName -X quit
