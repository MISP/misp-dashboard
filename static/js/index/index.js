var feedStatusFreqCheck = 1000*15;
var maxNumPoint = hours_spanned;
var keepaliveTime = 0;
var emptyArray = [];
var _timeoutLed;
var toPlotLocationLog;
for(i=0; i<maxNumPoint; i++) {
    emptyArray.push([i, 0]);
}

class LedManager {
    constructor() {
        this._feedLedsTimeout = setTimeout(function(){ ledmanager.manageColors(); }, feedStatusFreqCheck);
        this._feedLedKeepAlive = {};
        this._allFeedName = [];
        this._ledNum = 0;
        this._nameToNumMapping = {}; //avoid bad ID if zmqname contains spaces
    }

    add_new_led(zmqname) {
        this._allFeedName.push(zmqname);
        this._nameToNumMapping[zmqname] = this._ledNum;
        this._ledNum += 1;
        this.add_new_html_led(zmqname);
        this._feedLedKeepAlive[zmqname] = new Date().getTime();
    }

    add_new_html_led(zmqname) {
        var ID = this._nameToNumMapping[zmqname]
        var text = document.createElement('b');
        text.innerHTML = zmqname;
        var div = document.createElement('DIV');
        div.id = "status_led_"+ID;
        div.classList.add("led_green");
        var sepa = document.createElement('DIV');
        sepa.classList.add("leftSepa");
        sepa.classList.add("textTopHeader");
        sepa.appendChild(text);
        sepa.appendChild(div);
        $('#ledsHolder').append(sepa);
    }

    updateKeepAlive(zmqname) {
        if (this._allFeedName.indexOf(zmqname) == -1) {
            this.add_new_led(zmqname);
        }
        this._feedLedKeepAlive[zmqname] = new Date().getTime();
        this.resetTimeoutAndRestart(zmqname);
    }

    resetTimeoutAndRestart(zmqName) {
        clearTimeout(this._feedLedsTimeout); //cancel current leds timeout
        this.manageColors();
    }

    manageColors() {
        for (var feed in this._feedLedKeepAlive) {
            var feedID = this._nameToNumMapping[feed];
            var htmlLed = $("#status_led_"+feedID);
            if(new Date().getTime() - this._feedLedKeepAlive[feed] > feedStatusFreqCheck) { // no feed
                htmlLed.removeClass("led_green");
                htmlLed.addClass("led_red");
            } else {
                htmlLed.removeClass("led_red");
                htmlLed.addClass("led_green");
            }
        }
        this._feedLedsTimeout = setTimeout(function(){ ledmanager.manageColors(); }, feedStatusFreqCheck);
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
            if(src == 'global') //ignore global
                continue;
            var realData = this._sourcesArray[src].slice(0); //clone array
            realData.push([maxNumPoint, 0]);
            to_return.push({
                label: src,
                data: realData
            });
        }
        return to_return;
    }

    toArrayDirect() {
        var to_return = [];
        for (var src of this._sourceNames) {
            if(src == 'global') //ignore global
                continue;
            var realData = this._sourcesArray[src].slice(0); //clone array
            realData.push([maxNumPoint, this._sourcesCount[src]]);
            this._globalMax = this._globalMax > this._sourcesCount[src] ? this._globalMax : this._sourcesCount[src];
            to_return.push({
                label: src,
                data: realData
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

/* END CLASS SOURCE */

var sources = new Sources();
sources.addSource('global');
var ledmanager = new LedManager();

var curNumLog = 0;
var curMaxDataNumLog = 0;
var source_log;

function connect_source_log() {
    source_log = new EventSource(urlForLogs);

    source_log.onopen = function(){
        //console.log('connection is opened. '+source_log.readyState);  
    };

    source_log.onerror = function(){
        console.log('error: '+source_log.readyState);  
        setTimeout(function() { connect_source_log(); }, 5000);
    };

    source_log.onmessage = function(event) {
        var json = jQuery.parseJSON( event.data );
        updateLogTable(json.feedName, json.log, json.zmqName);
    };
}

$(document).ready(function () {
    createHead(function() {
        if (!!window.EventSource) {
            connect_source_log();
        } else {
            console.log("No event source_log");
        }

    });

});


//  LOG TABLE
function updateLogTable(feedName, log, zmqName) {
    if (log.length == 0)
        return;

    // update keepAlives
    ledmanager.updateKeepAlive(zmqName);

    // Create new row
    tableBody = document.getElementById('table_log_body');

    // only add row for attribute
    if (feedName == "Attribute" ) {
        var categName = log[toPlotLocationLog];
        sources.addIfNotPresent(categName);
        sources.incCountOnSource(categName);
        sources.incCountOnSource('global');
        updateChartDirect();
        createRow(tableBody, log);

        // Remove old row
        while ($("#table_log").height() >= $("#panelLogTable").height()-26){ //26 for margin
            tableBody.deleteRow(0);
        }

    } else if (feedName == "Keepalive") {
        // do nothing
    } else {
        // do nothing
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

function getTextColour(rgb) {
    var r = parseInt('0x'+rgb.substring(0,2));
    var g = parseInt('0x'+rgb.substring(2,4));
    var b = parseInt('0x'+rgb.substring(4,6));
    var avg = ((2 * r) + b + (3 * g))/6;
    if (avg < 128) {
        return 'white';
    } else {
        return 'black';
    }
}

function addObjectToLog(name, obj, td) {
    if(name == "Tag") {
        var a = document.createElement('A');
        a.classList.add('tagElem');
        a.style.backgroundColor = obj.colour;
        a.style.color = getTextColour(obj.colour.substring(1,6));
        a.innerHTML = obj.name;
        td.appendChild(a);
        td.appendChild(document.createElement('br'));
    } else if (name == "mispObject") {
        td.appendChild(document.createTextNode('mispObj'));
    } else {
        td.appendChild(document.createTextNode('nop'));

    }
}

function createRow(tableBody, log) {
    var tr = document.createElement('TR');

    for (var key in log) {
        if (log.hasOwnProperty(key)) {
            var td = document.createElement('TD');
            if(typeof log[key] === 'object') { //handle list of objects
                theObj = log[key];
                for(var objI in theObj.data) {
                    addObjectToLog(theObj.name, theObj.data[objI], td);
                }

            } else {
                var textToAddArray = log[key].split(char_separator);
                for(var i in textToAddArray){
                    if (i > 0)
                        td.appendChild(document.createElement("br"));
                    td.appendChild(document.createTextNode(textToAddArray[i]));
                }
            }
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

    tableBody.appendChild(tr);

}

function createHead(callback) {
    if (document.getElementById('table_log_head').childNodes.length > 1)
        return
    $.getJSON( urlForHead, function( data ) {
        var tr = document.createElement('TR');
        for (i in data) {
            var head = data[i];
            var th = document.createElement('TH');
            if (head == itemToPlot) {
                toPlotLocationLog = i;
            }
            th.appendChild(document.createTextNode(head));
            tr.appendChild(th);
        }
        document.getElementById('table_log_head').appendChild(tr);
        callback();
    });
}
