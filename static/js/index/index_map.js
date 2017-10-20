var maxNumCoord = 100;
var max_img_rotation = 10;
var rotation_time = 1000*10; //10s

var mymap = L.map('feedDivMap1').setView([51.505, -0.09], 13);;
var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var osmAttrib='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var osm = new L.TileLayer(osmUrl, {minZoom: 3, maxZoom: 17, attribution: osmAttrib}).addTo(mymap);

var coord_to_change = 0;
var coord_array = [];
var first_map = true;
var map_lat, map_lon; //current lat and lon shown in openStreetMap pannel

/* MAP */
var mapObj;
var curNumMarker = 0;
var allMarker = [];

function marker_animation(x, y, curNumMarker) {
    var markerColor = mapObj.markers[curNumMarker].element.config.style.current.fill;
    $("#feedDiv2").append(
        $('<div class="marker_animation"></div>')
        .css({'left': x-15 + 'px'}) /* HACK to center the effect */
        .css({'top': y-15 + 'px'})
        .css({ 'background-color': markerColor })
        .animate({ opacity: 0, scale: 1, height: '80px', width:'80px', margin: '-25px' }, 700, 'linear', function(){$(this).remove(); })
    );
}

// Add makers on the map
function popupCoord(coord) {
    var coord = [coord['lat'], coord['lon']];
    var value = Math.random()*180;
    pnts = mapObj.latLngToPoint(coord[0], coord[1])
    if (pnts != false) { //sometimes latLngToPoint return false
        mapObj.addMarker(curNumMarker, coord, [value]);
        allMarker.push(curNumMarker)
        marker_animation(pnts.x, pnts.y, curNumMarker);
        curNumMarker = curNumMarker>=maxNumCoord ? 0 : curNumMarker+1;
        if (allMarker.length >= maxNumCoord) {
            to_remove = allMarker[0];
            mapObj.removeMarkers([to_remove]);
            allMarker = allMarker.slice(1);
        }
    }
}

// Makes an animation on the marker concerned by the map shown in the openStreetMap pannel
function ping() {
    pnts = mapObj.latLngToPoint(map_lat, map_lon);
    if (pnts != false) { //sometimes latLngToPoint return false
        $("#feedDiv2").append(
                $('<div class="marker_animation"></div>')
                .css({'left': pnts.x-15 + 'px'}) /* HACK to center the effect */
                .css({'top': pnts.y-15 + 'px'})
                .css({ 'background-color': 'orange' })
                .animate({ opacity: 0, scale: 1, height: '80px', width:'80px', margin: '-25px' }, 400, 'linear', function(){$(this).remove(); })
        );
    }
    setTimeout(function(){ ping(); }, rotation_time/4);
}

// Perform the roration of the map in the openStreetMap pannel
function rotate_map() {
    var to_switch = coord_array[coord_to_change];
    var coord = to_switch[0];
    map_lat = coord.lat;
    map_lon = coord.lon;
    var marker = to_switch[1];
    var headerTxt = to_switch[2];
    mymap.setView([coord.lat, coord.lon], 17);

    $("#textMap1").fadeOut(400, function(){ $(this).text(headerTxt); }).fadeIn(400);
    coord_to_change = coord_to_change == coord_array.length-1 ? 0 : coord_to_change+1;

    setTimeout(function(){ rotate_map(); }, rotation_time);
}



$(function(){
    $('#feedDiv2').vectorMap({
        map: 'world_mill',
        markers: [],
        series: {
          markers: [{
            attribute: 'fill',
            scale: ['#1A0DAB', '#e50000', '#62ff41'],
            values: [],
            min: 0,
            max: 180
          }],
        },
    });
    mapObj = $("#feedDiv2").vectorMap('get','mapObject');
});

// Subscribe to the flask eventStream
var source_map = new EventSource(urlForMaps);
source_map.onmessage = function(event) {
    var json = jQuery.parseJSON( event.data );
    popupCoord(json.coord);
    var img2 = linkForDefaultMap.replace(/\/[^\/]+$/, "/"+json.path);
    
    if (coord_array.len >= max_img_rotation) {
        coord_array[0][1].remove() // remove marker
        coord_array.slice(1)
    }
    var marker = L.marker([json.coord.lat, json.coord.lon]).addTo(mymap);
    coord_array.push([json.coord, marker, ""+json.coord.lat+", "+json.coord.lon]);

    if (first_map) { // remove no_map pic
        rotate_map();
        ping();
        first_map = false;
    }
};
source_map.onopen = function(){
    console.log('connection is opened. '+source_map.readyState);  
};
source_map.onerror = function(){
    console.log('error: '+source_map.readyState);  
};
