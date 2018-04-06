#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DASH_HOME="${DIR}/.."


./start_framework.sh
# Wait a bit that redis terminate
sleep 1
python test_geo.py
python test_users.py
python test_trendings.py
./terminate_framework.sh
