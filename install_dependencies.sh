#!/bin/bash

set -e
#set -x

sudo chmod -R g+w . 

if ! id zmqs >/dev/null 2>&1; then
	# Create zmq user
	sudo useradd -U -G www-data -m -s /bin/bash  zmqs
	# Adds right to www-data to run ./start-zmq as zmq
	if gcc --version | grep -E "ubuntu|debian|kali";then
		sudo echo "www-data ALL=(zmqs)	NOPASSWD:/bin/bash	/var/www/misp-dashboard/start_zmq.sh" > /etc/sudoers.d/www-data
	elif gcc --version | grep -E "Red Hat|Cent OS";then
		sudo echo "www-data ALL=(zmqs)	NOPASSWD:/bin/bash	/var/www/misp-dashboard/start_zmq.sh" | sudo EDITOR='tee -a' visudo
	fi
fi

sudo apt-get install python3-virtualenv virtualenv screen redis-server unzip -y

if [ -z "$VIRTUAL_ENV" ]; then
    virtualenv -p python3 DASHENV

    . ./DASHENV/bin/activate
fi

pip3 install -U -r requirements.txt

## config
if [ -e "config/config.cfg" ]; then
    diff -u config/config.cfg.default config/config.cfg
    if [ "$?" == "0" ]; then
        cp -f config/config.cfg.default config/config.cfg
    else
        echo "Your config has changes, giving you a chance to see the changes and decide if you want to overwrite"
        cp -i config/config.cfg.default config/config.cfg
    fi
else
    cp -i config/config.cfg.default config/config.cfg
    echo "Sanitizing MaxMindDB Path"
    sed -i "s|pathMaxMindDB=./data/GeoLite2-City/GeoLite2-City.mmdb|pathMaxMindDB=$PWD/data/GeoLite2-City/GeoLite2-City.mmdb|" config/config.cfg
    sed -i "s|path_countrycode_to_coord_JSON=./data/country_code_lat_long.json|path_countrycode_to_coord_JSON=$PWD/data/country_code_lat_long.json|" config/config.cfg
fi

## Web stuff
pushd static/
mkdir -p css fonts js
popd
mkdir -p temp

wget http://www.misp-project.org/assets/images/misp-small.png -O static/pics/MISP.png

# jquery
JQVERSION="3.2.1"
wget http://code.jquery.com/jquery-${JQVERSION}.min.js -O ./static/js/jquery.min.js

# jquery flot
FLOTVERSION="0.8.3"
wget http://www.flotcharts.org/downloads/flot-${FLOTVERSION}.zip -O ./temp/flot-${FLOTVERSION}.zip
unzip -o temp/flot-${FLOTVERSION}.zip -d temp/
mv temp/flot/jquery.flot.js ./static/js
mv temp/flot/jquery.flot.pie.min.js ./static/js
mv temp/flot/jquery.flot.resize.js ./static/js
mv temp/flot/jquery.flot.time.js ./static/js

# jquery UI
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
mv temp/startbootstrap-sb-admin-2-${SBADMIN_VERSION}/bower_components/font-awesome/css/* ./static/css
mv temp/startbootstrap-sb-admin-2-${SBADMIN_VERSION}/bower_components/bootstrap/fonts/* ./static/fonts

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

# maxmind DB
rm -rf data/GeoLite2-City*
mkdir -p data
pushd data
wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz -O GeoLite2-City.tar.gz
tar xvfz GeoLite2-City.tar.gz
ln -s GeoLite2-City_* GeoLite2-City
rm -rf GeoLite2-City.tar.gz
popd

# DataTable
DATATABLE_VERSION="1.10.16"
wget https://cdn.datatables.net/${DATATABLE_VERSION}/js/jquery.dataTables.min.js -O ./static/js/jquery.dataTables.min.js
wget https://cdn.datatables.net/${DATATABLE_VERSION}/css/dataTables.bootstrap.css -O ./static/css/dataTables.bootstrap.css
wget https://cdn.datatables.net/${DATATABLE_VERSION}/js/dataTables.bootstrap.js -O ./static/js/dataTables.bootstrap.js

#typeahead
git clone https://github.com/bassjobsen/Bootstrap-3-Typeahead.git temp/Bootstrap-3-Typeahead
mv temp/Bootstrap-3-Typeahead/bootstrap3-typeahead.min.js ./static/js

#punchcard
git clone https://github.com/melenaos/jquery-punchcard.git temp/jquery-punchcard
mv temp/jquery-punchcard/src/punchcard.js ./static/js
mv temp/jquery-punchcard/src/punchcard.css ./static/css
wget https://momentjs.com/downloads/moment.js -O ./static/js/moment.js

# timeline
VISJS_VERSION="4.21.0"
wget https://cdnjs.cloudflare.com/ajax/libs/vis/${VISJS_VERSION}/vis.min.js -O ./static/js/vis.min.js
wget https://cdnjs.cloudflare.com/ajax/libs/vis/${VISJS_VERSION}/vis.min.css -O ./static/css/vis.min.css

rm -rf ./temp
