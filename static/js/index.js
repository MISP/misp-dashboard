
var updateInterval = 30; // 30ms
var numPoint = 10;
var emptyArray = [];
for(i=0; i<numPoint; i++) {
    emptyArray.push(0);
}
var data = { 'undefined': { label: 'undefined', data: [] } };
var curMax = { 'undefined': [] };
var optionsGraph = {
    series: {
                shadowSize: 0 ,
                lines: { fill: true, fillColor: { colors: [ { opacity: 1 }, { opacity: 0.1 } ] }}
            },
    yaxis: { min: 0, max: 20 },
    xaxis: { ticks: [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8], [9, 9], [10, 10]] },
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
                updateLogTable(json.log);
                //updateChartData(json.chart);
            };
        
        } else {
            console.log("No event source");
        }
    });
});


//var plot = $.plot("#placeholder", [ [] ], optionsGraph);
//updateChart()

function updateChart() {
    plot.setData(data);
    plot.getOptions().yaxes[0].max = curMax[dataset];
    plot.setupGrid();
    plot.draw();
    setTimeout(update, updateInterval);
}

function updateChartData(feed) {
    if (feed.length == 0)
        return;

    for (feedName in feed) {
        console.log(feedName.name);
        if (data[feedName.name] === undefined) {
            data[feedName.name] = {};
        }
        data[feedName.name].data = slide(data[feedName.name].data, feedName.data)
    }

}

function updateLogTable(log) {
    if (log.length == 0)
        return;

    // Create new row
    tableBody = document.getElementById('table_log_body');
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
    var slided = orig;
    slided.slice(newData.length);
    slided.concat(newData);
    return slided
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
