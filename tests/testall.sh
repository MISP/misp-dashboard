#!/bin/bash
set -e
[ -z "$DASH_HOME" ] && echo "Needs the env var DASHENV. Run the script from the virtual environment." && exit 1;

./start_framework.sh
# Wait a bit that redis terminate
sleep 1
python test_geo.py
python test_users.py
python test_trendings.py
./terminate_framework.sh
