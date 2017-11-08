#!/bin/bash

set -e
set -x

sudo apt-get install python3-virtualenv -y

if [ -z "$VIRTUAL_ENV" ]; then
    virtualenv -p python3 DASHENV

    echo export DASH_HOME=$(pwd) >> ./DASHENV/bin/activate
    echo export DASH_CONFIG=$(pwd)/config/ >> ./DASHENV/bin/activate

    . ./DASHENV/bin/activate
fi

pip3 install -U pip argparse redis zmq geoip2 flask

## config
if [ ! -f config/config.cfg ]; then
    cp config/config.cfg.sample config/config.cfg
fi

## Web stuff
pushd static/
mkdir -p css fonts
popd
mkdir -p temp

wget http://www.misp-project.org/assets/images/misp-small.png -O static/pics/MISP.png

# jquery
JQVERSION="3.2.1"
wget http://code.jquery.com/jquery-${JQVERSION}.min.js -O ./static/js/jquery.min.js

FLOTVERSION="0.8.3"
wget http://www.flotcharts.org/downloads/flot-${FLOTVERSION}.zip -O ./temp/flot-${FLOTVERSION}.zip
unzip -o temp/flot-${FLOTVERSION}.zip -d temp/
mv temp/flot/jquery.flot.js ./static/js
mv temp/flot/jquery.flot.pie.min.js ./static/js
mv temp/flot/jquery.flot.resize.js ./static/js


JQUERYUIVERSION="1.12.1"
wget https://jqueryui.com/resources/download/jquery-ui-${JQUERYUIVERSION}.zip -O temp/jquery-ui.zip
unzip -o temp/jquery-ui.zip -d temp/
mv temp/jquery-ui-${JQUERYUIVERSION}/jquery-ui.min.js ./static/js/jquery-ui.min.js
mv temp/jquery-ui-${JQUERYUIVERSION}/jquery-ui.min.css ./static/css/jquery-ui.min.css
mkdir -p static/css/images
mv -f temp/jquery-ui-${JQUERYUIVERSION}/images/* ./static/css/images/

# boostrap
#BOOTSTRAP_VERSION='4.0.0-beta.2'
#wget https://github.com/twbs/bootstrap/releases/download/v${BOOTSTRAP_VERSION}/bootstrap-${BOOTSTRAP_VERSION}-dist.zip -O temp/bootstrap-${BOOTSTRAP_VERSION}.zip
#unzip -o temp/bootstrap-${BOOTSTRAP_VERSION}.zip -d temp/bootstrap-${BOOTSTRAP_VERSION}-dist/
#mv temp/bootstrap-${BOOTSTRAP_VERSION}-dist/js/* ./static/js/
#mv temp/bootstrap-${BOOTSTRAP_VERSION}-dist/css/* ./static/css/

# sb-admin2
SBADMIN_VERSION='3.3.7'
wget https://github.com/BlackrockDigital/startbootstrap-sb-admin-2/archive/v${SBADMIN_VERSION}.zip -O temp/${SBADMIN_VERSION}-2.zip
unzip -o temp/${SBADMIN_VERSION}-2.zip -d temp/

mv temp/startbootstrap-sb-admin-2-${SBADMIN_VERSION}/dist/js/* ./static/js/
mv temp/startbootstrap-sb-admin-2-${SBADMIN_VERSION}/dist/css/* ./static/css/
mv temp/startbootstrap-sb-admin-2-${SBADMIN_VERSION}/bower_components/font-awesome/fonts/* ./static/fonts

# leaflet
LEAFLET_VERSION="1.2.0"
wget http://cdn.leafletjs.com/leaflet/v${LEAFLET_VERSION}/leaflet.zip -O temp/leaflet.zip
unzip -o temp/leaflet.zip -d temp/

mv temp/leaflet.js ./static/js/
mv temp/leaflet.css ./static/css/
mv temp/images/* ./static/css/images/

# jvectormap
JVECTORMAP_VERSION="2.0.3"
wget http://jvectormap.com/binary/jquery-jvectormap-${JVECTORMAP_VERSION}.zip -O temp/jquery-jvectormap-${JVECTORMAP_VERSION}
unzip -o temp/jquery-jvectormap-${JVECTORMAP_VERSION} -d temp/
mv temp/jquery-jvectormap-2.0.3.css ./static/css
mv temp/jquery-jvectormap-2.0.3.min.js ./static/js
wget http://jvectormap.com/js/jquery-jvectormap-world-mill.js -O ./static/js/jquery-jvectormap-world-mill.js

mkdir -p data
pushd data
wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz -O GeoLite2-City.tar.gz
tar xvfz GeoLite2-City.tar.gz
rm -rf GeoLite2-City.tar.gz
rm -rf ./temp
