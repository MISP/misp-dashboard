//color: #5f6062
var updateInterval = 1000*graph_log_refresh_rate; // 1s
var maxNumPoint = 60;
var maxNumCoord = 100;

var emptyArray = [];
var mapCoord = [];
var mapVal = [];
for(i=0; i<maxNumPoint; i++) {
    emptyArray.push([i, 0]);
    if (i<20) {
        mapCoord.push([]);
        mapVal.push(0);
    }
}

class Sources {
    constructor() {
        this._sourcesArray = {};
        this._sourcesCount = {};
        this._sourcesCountMax = {};
        this._globalMax = 0;
        this._sourceNames = [];
    }

    addSource(sourceName) {
        this._sourcesArray[sourceName] = emptyArray;
        this._sourcesCount[sourceName] = 0;
        this._sourcesCountMax[sourceName] = 0;
        this._sourceNames.push(sourceName);
    }

    addIfNotPresent(sourceName) {
        if (this._sourceNames.indexOf(sourceName) == -1) {
            this.addSource(sourceName);
        }
    }

    incCountOnSource(sourceName) {
        this._sourcesCount[sourceName] += 1;
    }

    resetCountOnSource() {
        for (var src of this._sourceNames) {
            this._sourcesCount[src] = 0;
        }
    }

    slideSource() {
        var globMax = 0;
        for (var src of this._sourceNames) {
            // res[0] = max, res[1] = slidedArray
            var res = slideAndMax(this._sourcesArray[src], this._sourcesCount[src]);
            // max
            this._sourcesCountMax[src] = res[0];
            globMax = globMax > res[0] ? globMax : res[0];
            // data
            this._sourcesArray[src] = res[1];
        }
        this._globalMax = globMax;
    }

    toArray() {
        var to_return = [];
        for (var src of this._sourceNames) {
            to_return.push({
                label: src,
                data: this._sourcesArray[src]
            });
        }
        return to_return;
    }

    getGlobalMax() {
        return this._globalMax;
    }

    getSingleSource(sourceName) {
        return this._sourcesArray[sourceName];
    }

    getEmptyData() {
        return [{label: 'no data', data: emptyArray}];
    }
}

var sources = new Sources();
sources.addSource('global');

var curNumLog = 0;
var curMaxDataNumLog = 0;

var optionsLineChart = {
    series: {
                shadowSize: 0 ,
                lines: { 
                    fill: true, 
                    fillColor: { 
                        colors: [ { opacity: 1 }, { opacity: 0.1 } ]
                    }
                }
            },
    //colors: ["#2fa1db"],
    yaxis: { min: 0, max: 20 },
    xaxis: { min: 0, max: maxNumPoint-1 },
    ticks: maxNumPoint,
    grid: {
        tickColor: "#dddddd",
        borderWidth: 0 
    },
    legend: {
        show: true,
        position: "nw"
    }
};

function labelFormatter(label, series) {
    return "<div style='font-size:8pt; text-align:center; padding:2px; color:white;'>"
+ label + "<br/>" + Math.round(series.percent) + "%</div>";
}
var optionsPieChart = {
    series: {
        pie: {
            innerRadius: 0.5,
            show: true,
            label: {
                show: true,
                radius: 1,
                formatter: labelFormatter,
                background: {
                    opacity: 0.7,
                    color: '#000'
                }
            }
        }
    },
    legend: {
        show: false
    }
};

$(document).ready(function () {
    createHead(function() {
        if (!!window.EventSource) {
            var source = new EventSource(urlForLogs);

            source.onopen = function(){
                //console.log('connection is opened. '+source.readyState);  
            };

            source.onerror = function(){
                //console.log('error: '+source.readyState);  
            };

            source.onmessage = function(event) {
                var json = jQuery.parseJSON( event.data );
                updateLogTable(json.feedName, json.log);
            };
        
        } else {
            console.log("No event source");
        }
    });
});

    var rData = [
        { label: "Series1",  data: 10},
        { label: "Series2",  data: 30},
        { label: "Series3",  data: 60}
    ];
var plotLineChart = $.plot("#feedDiv3", sources.getEmptyData(), optionsLineChart);
//var plotPieChartA = $.plot("#feedDiv1A", rData, optionsPieChart);
//var plotPieChartB = $.plot("#feedDiv1B", rData, optionsPieChart);
updateChart()

function updateChart() {
    updateChart1();
    updateChart2();
    setTimeout(updateChart, updateInterval);
}

function updateChart1() {
    sources.slideSource();
    sources.resetCountOnSource();
    plotLineChart.setData(sources.toArray());
    plotLineChart.getOptions().yaxes[0].max = sources.getGlobalMax();
    plotLineChart.setupGrid();
    plotLineChart.draw();
}

function updateChart2() {

}

function updateLogTable(feedName, log) {
    if (log.length == 0)
        return;

    // Create new row
    tableBody = document.getElementById('table_log_body');
    //curNumLog++;
    sources.addIfNotPresent(feedName);
    sources.incCountOnSource(feedName);
    sources.incCountOnSource('global');
    createRow(tableBody, log);

    // Remove old row
    var logSel = document.getElementById("log_select");
    //get height of pannel, find max num of item
    var maxNumLogItem = document.getElementById('divLogTable').clientHeight/37;
    maxNumLogItem -= 2; //take heading/padding/... into account
    if (maxNumLogItem - parseInt(maxNumLogItem) < 0.5) { //beautifier
        maxNumLogItem -= 1;
    }
    if (tableBody.rows.length > maxNumLogItem) {
        while (tableBody.rows.length >= maxNumLogItem){
            tableBody.deleteRow(0);
        }
    }

}

function slideAndMax(orig, newData) {
    var slided = [];
    var max = newData;
    for (i=1; i<orig.length; i++) {
        y = orig[i][1];
        slided.push([i-1, y]);
        max = y > max ? y : max;
    }
    slided.push([orig.length-1, newData]);
    curMaxDataNumLog = max;
    return [curMaxDataNumLog, slided];
}

function createRow(tableBody, log) {
    var tr = document.createElement('TR');
    var action = document.createElement('TD');
    var x = log[1];
    var y = log[2];
    popupCoord([x,y]);

    for (var key in log) {
        if (log.hasOwnProperty(key)) {
            var td = document.createElement('TD');
            td.appendChild(document.createTextNode(log[key]));
            tr.appendChild(td);
        }
    }

    // level
    if( log.level == "INFO" ){
        tr.className = "info";
    }
    else if ( log.level == "WARNING" ){
        tr.className = "warning";
    }
    else if ( log.level == "CRITICAL"){
        tr.className = "danger"
    }

    // action
    action.appendChild(document.createTextNode("ACTION"));
    tr.appendChild(action);

    tableBody.appendChild(tr);

}

function createHead(callback) {
    if (document.getElementById('table_log_head').childNodes.length > 1)
        return
    $.getJSON( urlForHead, function( data ) {
        var tr = document.createElement('TR');
        for (head of data) {
            var th = document.createElement('TH');
            th.appendChild(document.createTextNode(head));
            tr.appendChild(th);
        }
        var action = document.createElement('TH');
        action.appendChild(document.createTextNode("Actions"));
        tr.appendChild(action);
        document.getElementById('table_log_head').appendChild(tr);
        callback();
    });
}


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
        .animate({ opacity: 0, scale: 1, height: '80px', width:'80px', margin: '-25px' }, 1000, 'linear', function(){$(this).remove(); })
    );
}

function popupCoord(coord) {
    var value = coord[0]+coord[1];
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


$(function(){
    $('#feedDiv2').vectorMap({
        map: 'world_mill',
        markers: [],
        series: {
          markers: [{
            attribute: 'fill',
            scale: ['#1A0DAB', '#e50000', '#62ff41'],
            values: [],
            min: -180,
            max: 180
          }],
        },
    })
    mapObj = $("#feedDiv2").vectorMap('get','mapObject');
});
