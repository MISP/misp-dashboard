const OSMURL='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSMATTRIB='Map data © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
var ZOOMLEVEL = default_zoom_level;
var updateFrequency = 1000*60*default_updateFrequency //min

var regionhitsMax = 10;
var regionhits = {};
var allOpenStreetMap = {};
var savedMarker = {};
var savedMarkerRadius = [];
var datePickerWidget;
var datePickersRadiusWidget;
var radiusOpenStreetMap;
var circleRadius;

/* CONFIG */
var vectorMapConfig = {
    map: 'world_mill',
    markers: [],
    series: {
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
    onRegionTipShow: function(e, el, code){
      el.html(el.html()+' ('+regionhits[code]+')');
    }
}
var datePickerOptions = {
    showOn: "button",
    minDate: -31,
    maxDate: 0,
    buttonImage: urlIconCalendar,
    buttonImageOnly: true,
    buttonText: "Select date",
    showAnim: "slideDown",
    onSelect: updateAll
};
var datePickerRadiusOptions = {
    showOn: "button",
    minDate: -31,
    maxDate: 0,
    buttonImage: urlIconCalendar,
    buttonImageOnly: true,
    buttonText: "Select date",
    showAnim: "slideDown",
};
var circleRadiusOptions = {
    color: 'red',
    weight: 1,
    fillColor: '#f03',
    fillOpacity: 0.4,
}



/* START SCRIPTS */
$(document).ready(function () {
    // Page header
    $( "#zoom_selector" ).attr("selected", "selected");
    $( "#zoom_selector" ).change(function() {
        var sel = parseInt($( this ).val());
        ZOOMLEVEL = sel;
        updateAll();
    });
    datePickerWidget = $( "#datepicker" )
    datePickerWidget.datepicker(datePickerOptions);
    datePickerWidget.datepicker("setDate", new Date());

    /* Top location */
    for(var i=1; i<7; i++) {
        allOpenStreetMap[i] = L.map('topMap'+i).setView([0, 0], 0);
        new L.TileLayer(OSMURL, {minZoom: 0, maxZoom: 18}).addTo(allOpenStreetMap[i]);
    }

    // World map
    $('#worldMap').vectorMap(vectorMapConfig);
    worldMapObj = $("#worldMap").vectorMap('get','mapObject');

    // Radius
    radiusOpenStreetMap = L.map('radiusMap').setView([30, 0], 2);
    new L.TileLayer(OSMURL, {minZoom: 0, maxZoom: 18}).addTo(radiusOpenStreetMap);
    datePickersRadiusWidgetFrom = $( "#datepickerRadiusFrom" )
    datePickersRadiusWidgetFrom.datepicker(datePickerRadiusOptions);
    datePickersRadiusWidgetFrom.datepicker("setDate", new Date());
    datePickersRadiusWidgetTo = $( "#datepickerRadiusTo" )
    datePickersRadiusWidgetTo.datepicker(datePickerRadiusOptions);
    datePickersRadiusWidgetTo.datepicker("setDate", new Date());

    circleRadiusOptions['radius'] = getScale(radiusOpenStreetMap.getZoom());
    circleRadius = L.circle(radiusOpenStreetMap.getCenter(), circleRadiusOptions).addTo(radiusOpenStreetMap);
    radiusOpenStreetMap.on('move', updateRadius);

    // Start
    updateAll();
    setInterval(function(){ 
        updateAll(); 
        $("#alertUpdate").fadeIn(2200).fadeOut(2200);
    }, updateFrequency);

});


/* TOP LOCATION */

function updateTopMaps(date) {
    $.getJSON(urlTopCoord+"?date="+date.getTime()/1000, function(list){
        if (list.length==0 && savedMarker[1]!=undefined) { //No data and new markers
            console.log(savedMarker.length);
            for(var i=0; i<6; i++) { // clear maps
                allOpenStreetMap[i+1].setView([0, 0], 1);
                savedMarker[i+1].remove(); // remove marker
            }
            savedMarker = {};
        }
        for(var i=0; i<6 && i<list.length; i++) {
            // create marker + flyToIt
            dataJson = JSON.parse(list[i][0]);
            categ = dataJson.categ === undefined ? "" : dataJson.categ;
            value = dataJson.value === undefined ? "" : dataJson.value;
            allOpenStreetMap[i+1].flyTo([dataJson.lat, dataJson.lon], ZOOMLEVEL);

            // update marker
            var markerToUpdate = savedMarker[i+1];
            if (markerToUpdate != undefined) {
                markerToUpdate.setLatLng({lat: dataJson.lat, lng: dataJson.lon});
                markerToUpdate._popup.setContent(categ+' - '+value+' (<strong>'+list[i][1]+'</strong>)');
                markerToUpdate.update();
            } else { // create new marker
                var marker = L.marker([dataJson.lat, dataJson.lon]).addTo(allOpenStreetMap[i+1]);
                savedMarker[i+1] = marker;
                marker.bindPopup(categ+' - '+value+' (<strong>'+list[i][1]+'</strong>)').openPopup();
            }
        }
    });
}


/* WORLD MAP */

function updateWorldMap(date) {
     $.getJSON(urlHitMap+"?date="+date.getTime()/1000, function(list){
        regionhits = {};
        worldMapObj.series.regions[0].clear();
        for(var i=0; i<list.length; i++) {
            var rCode = list[i][0];
            var rNum = list[i][1];
            update_region(rCode, rNum);
        }
    });   
}

function update_region(regionCode, num) {
    regionhits[regionCode] = num;
    // Force recomputation of min and max for correct color scaling
    worldMapObj.series.regions[0].params.max = undefined;
    worldMapObj.series.regions[0].legend.render();
    // Update data
    worldMapObj.series.regions[0].setValues(regionhits);
}


/* RADIUS MAP */

function updateRadius(e) {
    var curObj = e.target;
    var curCoord = curObj.getCenter();
    var zoom = curObj.zoom;
    var scale = getScale(radiusOpenStreetMap.getZoom());
    circleRadius.setRadius(scale);
    circleRadius.setLatLng(curCoord);
}

function getScale(zoom) {
    return 64 * Math.pow(2, (18-zoom));
}

function queryAndAddMarkers() {
    var radius_km = circleRadius.getRadius() / 1000;
    var coord = circleRadius._latlng;
    var dateStart = datePickersRadiusWidgetFrom.datepicker("getDate").getTime() / 1000;
    var dateEnd = datePickersRadiusWidgetTo.datepicker("getDate").getTime() / 1000;
    $.getJSON(urlCoordsByRadius+"?dateStart="+dateStart+"&dateEnd="+dateEnd+"&centerLat="+coord.lat+"&centerLon="+coord.lng+"&radius="+radius_km, function(allList){
        // remove old markers
        for (var i in savedMarkerRadius) {
            savedMarkerRadius[i].remove(); // remove marker
        }

        for (var listIndex in allList) {
            var curMarker = allList[listIndex];
            var dataText = "";
            var coordJson = curMarker[1];
            for (var dataI in curMarker[0]) {
                var jsonData = JSON.parse(curMarker[0][dataI])
                dataText += '<strong>'+jsonData.categ+': </strong> '+jsonData.value + "<br>"
            }
            var marker = L.marker([coordJson[1], coordJson[0]]).addTo(radiusOpenStreetMap);
            savedMarkerRadius.push(marker);
            marker.bindPopup(dataText, {autoClose:false}).openPopup();
        }
    });
}


/* UTIL */

function days_between(date1, date2) {
    var ONEDAY = 60*60*24*1000;
    var diff_ms = Math.abs(date1.getTime() - date2.getTime());
    return Math.round(diff_ms/ONEDAY);
}

function updateAll() {
    var currentDate = datePickerWidget.datepicker( "getDate" );
    var now = new Date();
    var numDay = days_between(now, currentDate);
    updateTopMaps(currentDate);
    updateWorldMap(currentDate);
}
