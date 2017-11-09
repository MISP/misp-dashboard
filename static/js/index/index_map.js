const MAXNUMCOORD = 100;
const PINGWAITTIME = 1000*1; //1s
const MAXIMGROTATION = parseInt(max_img_rotation);

const OSMURL='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSMATTRIB='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var ROTATIONWAITTIME = 1000*rotation_wait_time; //seconds
var ZOOMLEVEL = zoomlevel;
var regionhits = {};
var regionhitsMax = 10;

var myOpenStreetMap = L.map('feedDivMap1').setView([0, 0], 1);
var osm = new L.TileLayer(OSMURL, {minZoom: 0, maxZoom: 18}).addTo(myOpenStreetMap);

class MapEvent {
    constructor(json, marker) {
        this.coord = json.coord;
        this.regionCode = json.regionCode;
        this.marker = marker;
        this.categ = json.categ;
        this.value = json.value;
        this.country = json.country;
        this.specifName = json.specifName;
        this.cityName = json.cityName;
        this.text = this.categ + ": " + this.value;
        this.textMarker = "<b>{1}</b><br>{2}".replace("{1}", this.country).replace("{2}", this.specifName+", "+this.cityName);
    }
}

class MapEventManager {
    constructor() {
        this._mapEventArray = [];
        this._currentMapEvent;
        this._nextEventToShow = 0;
        this._first_map = true;
        this._coordSet = new Set();
        //current lat and lon shown in worldMap
        this._latToPing;
        this._lonToPing;
        //Markers on the worldMap
        this._allMarkers = [];
        this._curMarkerNum = 0;
        //use for cancelTimeout
        this._timeoutRotate;
    }

    addMapEvent(mapevent) {
        if(this.getNumberOfEvent() > MAXIMGROTATION) {
            var toDel = this._mapEventArray[0];
            toDel.marker.remove(); // remove marker
            this._coordSet.delete(toDel.text);
            this._mapEventArray = this._mapEventArray.slice(1);
        }

        if(!this._coordSet.has(mapevent.text)) { // avoid duplicate map
            this._mapEventArray.push(mapevent);
            this._coordSet.add(mapevent.text);
            this.popupCoord(mapevent.coord, mapevent.regionCode);
        } else {
            //console.log('Duplicate coordinates');
        }

        if(this._first_map) { // remove no_map pic
            this.rotateMap();
            this.ping();
            this._first_map = false;
        } else {
            this.rotateMap(mapevent);
        }
    }

    getNumberOfEvent() {
        return this._mapEventArray.length
    }

    getNextEventToShow() {
        var toShow = this._mapEventArray[this._nextEventToShow];
        this._nextEventToShow = this._nextEventToShow == this._mapEventArray.length-1 ? 0 : this._nextEventToShow+1;
        this._currentMapEvent = toShow;
        return toShow;
    }

    getCurrentMapEvent() {
        return this._currentMapEvent;
    }

    // Perform the roration of the map in the openStreetMap pannel
    rotateMap(mapEvent) {
        clearTimeout(this._timeoutRotate); //cancel current map rotation
        if (mapEvent == undefined) {
            var mapEvent = this.getNextEventToShow();
        }
        this._latToPing = mapEvent.coord.lat;
        this._lonToPing = mapEvent.coord.lon;
        var marker = mapEvent.marker;
        myOpenStreetMap.flyTo([mapEvent.coord.lat, mapEvent.coord.lon], ZOOMLEVEL);
        mapEvent.marker.bindPopup(mapEvent.textMarker).openPopup();

        $("#textMap1").text(mapEvent.text);
        if(ROTATIONWAITTIME != 0) {
            this._timeoutRotate = setTimeout(function(){ mapEventManager.rotateMap(); }, ROTATIONWAITTIME);
        }
    }

    directZoom() {
        var mapEvent = this.getCurrentMapEvent();
        if (mapEvent != undefined)
            myOpenStreetMap.flyTo([mapEvent.coord.lat, mapEvent.coord.lon], ZOOMLEVEL);
    }

    ping() {
        var pnts = openStreetMapObj.latLngToPoint(this._latToPing, this._lonToPing);
        if (pnts != false) { //sometimes latLngToPoint return false
            $("#feedDiv2").append(
                    $('<div class="marker_animation"></div>')
                    .css({'left': pnts.x-15 + 'px'}) /* HACK to center the effect */
                    .css({'top': pnts.y-15 + 'px'})
                    .css({ 'background-color': 'orange' })
                    .animate({ opacity: 0, scale: 1, height: '80px', width:'80px', margin: '-25px' }, 400, 'linear', function(){$(this).remove(); })
            );
        }
        setTimeout(function(){ mapEventManager.ping(); }, PINGWAITTIME);
    }

    // Add and Manage markers on the map + make Animation
    popupCoord(coord, regionCode) {
        var coord = [coord.lat, coord.lon];
        var color = 0.5*180;
        var pnts = openStreetMapObj.latLngToPoint(coord[0], coord[1])
        if (pnts != false) { //sometimes latLngToPoint return false
            var addedMarker = openStreetMapObj.addMarker(this._curMarkerNum, coord, [color]);
            this._allMarkers.push(this._curMarkerNum)
            marker_animation(pnts.x, pnts.y, this._curMarkerNum);
            update_region(regionCode);


            this._curMarkerNum = this._curMarkerNum >= MAXNUMCOORD ? 0 : this._curMarkerNum+1;
            if (this._allMarkers.length >= MAXNUMCOORD) {
                var to_remove = this._allMarkers[0];
                openStreetMapObj.removeMarkers([to_remove]);
                this._allMarkers = this._allMarkers.slice(1);
            }
        }
    }
}

function marker_animation(x, y, markerNum) {
    var markerColor = openStreetMapObj.markers[markerNum].element.config.style.current.fill;
    $("#feedDiv2").append(
        $('<div class="marker_animation"></div>')
        .css({'left': x-15 + 'px'}) /* HACK to center the effect */
        .css({'top': y-15 + 'px'})
        .css({ 'background-color': markerColor })
        .animate({ opacity: 0, scale: 1, height: '80px', width:'80px', margin: '-25px' }, 700, 'linear', function(){$(this).remove(); })
    );
}

function update_region(regionCode) {
    if (regionCode in regionhits) {
        regionhits[regionCode] += 1;
    } else {
        regionhits[regionCode] = 1;
    }
    // Force recomputation of min and max for correct color scaling
    regionhitsMax = regionhitsMax >= regionhits[regionCode] ? regionhitsMax : regionhits[regionCode];
    openStreetMapObj.series.regions[0].params.max = regionhitsMax;
    // Update data
    openStreetMapObj.series.regions[0].setValues(regionhits);
}

var mapEventManager = new MapEventManager();
var openStreetMapObj;

$(function(){
    $('#feedDiv2').vectorMap({
        map: 'world_mill',
        markers: [],
        series: {
            markers: [{
              attribute: 'fill',
              //scale: ['#1A0DAB', '#e50000', '#62ff41'],
              scale: ['#ffff66'],
              values: [],
              min: 0,
              max: 180
            }],
            regions: [{
              values: [],
              min: 0,
              max: 10,
              scale: ['#003FBF','#0063BF','#0087BF','#00ACBF','#00BFAD','#00BF89','#00BF64','#00BF40','#00BF1C','#08BF00','#2CBF00','#51BF00','#75BF00','#99BF00','#BEBF00','#BF9B00','#BF7700','#BF5200','#BF2E00','#BF0900'],
              normalizeFunction: 'linear',
              legend: {
                  horizontal: true
              }
            }]
        },
    });
    openStreetMapObj = $("#feedDiv2").vectorMap('get','mapObject');
});

// Subscribe to the flask eventStream
var source_map;
function connect_source_map() {
    source_map = new EventSource(urlForMaps);
    source_map.onmessage = function(event) {
        var json = jQuery.parseJSON( event.data );
        var marker = L.marker([json.coord.lat, json.coord.lon]).addTo(myOpenStreetMap);
        var mapEvent = new MapEvent(json, marker);
        mapEventManager.addMapEvent(mapEvent);

    };
    source_map.onopen = function(){
        console.log('connection is opened. '+source_map.readyState);
    };
    source_map.onerror = function(){
        console.log('error: '+source_map.readyState);
        setTimeout(function() { connect_source_map(); }, 5000);
    };
}
connect_source_map()

$(document).ready(function () {
    $( "#rotation_wait_time_selector" ).change(function() {
        var sel = parseInt($( this ).val());
        if(isNaN(sel)) {
            rotation_wait_time = 0;
        } else {
            rotation_wait_time = sel;
        }
        var old = ROTATIONWAITTIME;
        ROTATIONWAITTIME = 1000*rotation_wait_time; //seconds
        if(old == 0) {
            mapEventManager._timeoutRotate = setTimeout(function(){ mapEventManager.rotateMap(); }, ROTATIONWAITTIME);
        }
    });

    $( "#zoom_selector" ).change(function() {
        var sel = parseInt($( this ).val());
        ZOOMLEVEL = sel;
        mapEventManager.directZoom();
    });
});
