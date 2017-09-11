//color: #5f6062
var updateInterval = 1000; // 1s
var numPoint = 60;

var emptyArray = [];
var dataNumLog = [];
for(i=0; i<numPoint; i++) {
    dataNumLog.push([i, 0]);
    emptyArray.push([i, 0]);
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
            var res = slide(this._sourcesArray[src], this._sourcesCount[src]);
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

var optionsGraph = {
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
    xaxis: { min: 0, max: numPoint-1 },
    ticks: numPoint,
    grid: {
        tickColor: "#dddddd",
        borderWidth: 0 
    },
    legend: {
        show: true,
        position: "nw"
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


//var plot1 = $.plot("#feedDiv1", [ { label: "Number of log messages", data: dataNumLog } ], optionsGraph);
var plot1 = $.plot("#feedDiv1", sources.getEmptyData(), optionsGraph);
updateChart()

function updateChart() {
    updateChart1();
    updateChart2();
    setTimeout(updateChart, updateInterval);
}

function updateChart1() {
    sources.slideSource();
    sources.resetCountOnSource();
    plot1.setData(sources.toArray());
    plot1.getOptions().yaxes[0].max = sources.getGlobalMax();
    plot1.setupGrid();
    plot1.draw();
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
    if (tableBody.rows.length > logSel.options[logSel.options.selectedIndex].value){
        while (tableBody.rows.length != logSel.options[logSel.options.selectedIndex].value){
            tableBody.deleteRow(0);
        }
    }

}

function slide(orig, newData) {
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
