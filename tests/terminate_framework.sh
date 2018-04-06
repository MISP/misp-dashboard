#!/bin/bash

set -e

GREEN="\\033[1;32m"
DEFAULT="\\033[0;39m"
RED="\\033[1;31m"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASH_HOME="${DIR}/..


conf_dir="${DASH_HOME}/config/"
redis_dir="${DASH_HOME}/../redis/src/"
redis_dir="../../redis/src/"
test_dir="${DASH_HOME}/tests/"
screenName="Misp-Dashboard-test"


bash -c $redis_dir'redis-cli -p 6260 shutdown'
screen -S $screenName -X quit
echo -e $GREEN"* Shutting down Redis servers"$DEFAULT

