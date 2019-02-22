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

// function connect_source_log() {
//     source_log = new EventSource(urlForLogs);
//
//     source_log.onopen = function(){
//         //console.log('connection is opened. '+source_log.readyState);
//     };
//
//     source_log.onerror = function(){
//         console.log('error: '+source_log.readyState);
//         setTimeout(function() { connect_source_log(); }, 5000);
//     };
//
//     source_log.onmessage = function(event) {
//         var json = jQuery.parseJSON( event.data );
//         updateLogTable(json.name, json.log, json.zmqName);
//     };
// }

var livelog;
$(document).ready(function () {
    // createHead(function() {
    //     if (!!window.EventSource) {
    //         $.getJSON( urlForLogs, function( data ) {
    //             data.forEach(function(item) {
    //                 updateLogTable(item.name, item.log, item.zmqName);
    //             });
    //             connect_source_log();
    //         });
    //     } else {
    //         console.log("No event source_log");
    //     }
    //
    // });

    $.getJSON(urlForHead, function(head) {
        livelog = new $.livelog($("#divLogTable"), {
            pollingFrequency: 5000,
            tableHeader: head,
            tableMaxEntries: 50,
            animate: false,
            preDataURL: urlForLogs,
            endpoint: urlForLogs
        });
    });


});


//  LOG TABLE
function updateLogTable(name, log, zmqName, ignoreLed) {
    if (log.length == 0)
        return;

    // update keepAlives
    if (ignoreLed !== true) {
        ledmanager.updateKeepAlive(zmqName);
    }

    // Create new row
    // tableBody = document.getElementById('table_log_body');

    // only add row for attribute
    if (name == "Attribute" ) {
        var categName = log[toPlotLocationLog];
        sources.addIfNotPresent(categName);
        sources.incCountOnSource(categName);
        sources.incCountOnSource('global');
        updateChartDirect();
        // createRow(tableBody, log);

        // Remove old row
        // while ($("#table_log").height() >= $("#panelLogTable").height()-26){ //26 for margin
        //     tableBody.deleteRow(0);
        // }

    } else if (name == "Keepalive") {
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



/* LIVE LOG */
(function(factory) {
        "use strict";
        if (typeof define === 'function' && define.amd) {
            define(['jquery'], factory);
        } else if (window.jQuery && !window.jQuery.fn.Livelog) {
            factory(window.jQuery);
        }
    }
    (function($) {
        'use strict';

        // Livelog object
        var Livelog = function(container, options) {
            this._default_options = {
                pollingFrequency: 5000,
                tableHeader: undefined,
                tableMaxEntries: undefined,
                animate: true
            }

            options.container = container;

            this.validateOptions(options);
            this._options = $.extend({}, this._default_options, options);

            // create table and draw header
            this.origTableOptions = {
                dom: "<'row'<'col-sm-12'<'dt-toolbar-led'>>>"
                        + "<'row'<'col-sm-12'tr>>",
                searching: false,
                paging:         false,
                "order": [[ 0, "desc" ]],
                responsive: true,
                columnDefs: [
                    { targets: 0, orderable: false },
                    { targets: '_all', searchable: false, orderable: false,
                        render: function ( data, type, row ) {
                            // return data +' ('+ row[3]+')';
                                var $toRet;
                                if (typeof data === 'object') {
                                    $toRet = $('<span></span>');
                                    data.data.forEach(function(cur, i) {
                                        switch (data.name) {
                                            case 'Tag':
                                                var $tag = $('<a></a>');
                                                $tag.addClass('tagElem');
                                                $tag.css({
                                                    backgroundColor: cur.colour,
                                                    color: getTextColour(cur.colour.substring(1,6))
                                                });
                                                $tag.text(cur.name)
                                                $toRet.append($tag);
                                                break;
                                            case 'mispObject':
                                                $toRet.append('MISP Object not supported yet')
                                                break;
                                            default:
                                                break;
                                        }
                                    });
                                    $toRet = $toRet[0].outerHTML;
                                } else if (data === undefined) {
                                        $toRet = '';
                                } else {
                                    var textToAddArray = data.split(char_separator);
                                    $toRet = '';
                                    textToAddArray.forEach(function(e, i) {
                                        if (i > 0) {
                                            $toRet += '<br>' + e;
                                        } else {
                                            $toRet += e;
                                        }
                                    });
                                }
                                return $toRet;
                           },
                    }
                ],
            };

            this.DOMTable = $('<table class="table table-striped table-bordered" style="width:100%"></table>');
            this._options.container.append(this.DOMTable);
            this.origTableOptions.columns = [];
            var that = this;
            this._options.tableHeader.forEach(function(field) {
                var th = $('<th>'+field+'</th>');
                that.origTableOptions.columns.push({ title: field });
            });
            this.dt = this.DOMTable.DataTable(this.origTableOptions);

            this.fetch_predata();

            // add status led
            this._ev_timer = null;
            this._ev_retry_frequency = this._options.pollingFrequency; // sec
            this._cur_ev_retry_count = 0;
            this._ev_retry_count_thres = 3;
            var led_container = $('<div class="led-container" style="margin-left: 10px;"></div>');
            var led = $('<div class="led-small led_red"></div>');
            this.statusLed = led;
            led_container.append(led);
            var header = this._options.container.parent().parent().find('.panel-heading');

            if (header.length > 0) { // add in panel header
                header.append(led_container);
            } else { // add over the map
                // this._options.container.append(led_container);
                led.css('display', 'inline-block');
                led_container.append($('<span>Status</span>')).css('float', 'left');
                $('.dt-toolbar-led').append(led_container)
            }
            this.data_source = undefined;

            this.connect_to_data_source();

        };

        Livelog.prototype = {
            constructor: Livelog,

            validateOptions: function(options) {
                var o = options;

                if (o.endpoint === undefined || typeof o.endpoint != 'string') {
                    throw "Livelog must have a valid endpoint";
                }

                if (o.container === undefined) {
                    throw "Livelog must have a container";
                } else {
                    o.container = o.container instanceof jQuery ? o.container : $('#'+o.container);
                }

                // pre-data is either the data to be shown or an URL from which the data should be taken from
                if (Array.isArray(o.preData)){
                    o.preDataURL = null;
                    o.preData = o.preData;
                } else if (o.preData !== undefined) { // should fetch
                    o.preDataURL = o.preData;
                    o.preData = [];
                }

                if (o.tableHeader === undefined || !Array.isArray(o.tableHeader)) {
                    throw "Livelog must have a valid header";
                }

                if (o.tableMaxEntries !== undefined) {
                    o.tableMaxEntries = parseInt(o.tableMaxEntries);
                }
            },

            fetch_predata: function() {
                var that = this;
                if (this._options.preDataURL !== null) {
                    $.when(
                        $.ajax({
                            dataType: "json",
                            url: this._options.preDataURL,
                            data: this._options.additionalOptions,
                            success: function(data) {
                                that._options.preData = data;
                            },
                            error: function(jqXHR, textStatus, errorThrown) {
                                console.log(textStatus);
                                that._options.preData = [];
                            }
                        })
                    ).then(
                        function() { // success
                            // add data to the widget
                            that._options.preData.forEach(function(j) {
                                var name = j.name,
                                    zmqName = j.zmqName,
                                    entry = j.log;
                                updateLogTable(name, entry, zmqName, true);
                                switch (name) {
                                    case 'Attribute':
                                        that.add_entry(entry);
                                        break;
                                    default:
                                        break;
                                }
                            });
                        }, function() { // fail
                        }
                    );
                }
            },

            connect_to_data_source: function() {
                var that = this;
                if (!this.data_source) {
                    // var url_param = $.param( this.additionalOptions );
                    this.data_source = new EventSource(this._options.endpoint);
                    this.data_source.onmessage = function(event) {
                        var json = jQuery.parseJSON( event.data );
                        var name = json.name,
                            zmqName = json.zmqName,
                            entry = json.log;
                        updateLogTable(name, entry, zmqName);
                        switch (name) {
                            case 'Attribute':
                                that.add_entry(entry);
                                break;
                            default:
                                break;
                        }
                    };
                    this.data_source.onopen = function(){
                        that._cur_ev_retry_count = 0;
                        that.update_connection_state('connected');
                    };
                    this.data_source.onerror = function(){
                        if (that.data_source.readyState == 0) { // reconnecting
                            that.update_connection_state('connecting');
                        }  else if (that.data_source.readyState == 2) { // closed, reconnect with new object
                            that.reconnection_logique();
                        } else {
                            that.update_connection_state('not connected');
                            that.reconnection_logique();
                        }
                    };
                }
            },

            reconnection_logique: function () {
                var that = this;
                if (that.data_source) {
                    that.data_source.close();
                    that.data_source = null;
                }
                if (that._ev_timer) {
                    clearTimeout(that._ev_timer);
                }
                if(that._cur_ev_retry_count >= that._ev_retry_count_thres) {
                    that.update_connection_state('not connected');
                } else {
                    that._cur_ev_retry_count++;
                    that.update_connection_state('connecting');
                }
                that._ev_timer = setTimeout(function () { that.connect_to_data_source(); }, that._ev_retry_frequency*1000);
            },

            reconnect: function() {
                if (this.data_source) {
                    this.data_source.close();
                    this.data_source = null;
                    this._cur_ev_retry_count = 0;
                    this.update_connection_state('reconnecting');
                    this.connect_to_data_source();
                }
            },

            update_connection_state: function(connectionState) {
                this.connectionState = connectionState;
                this.updateDOMState(this.statusLed, connectionState);
            },

            updateDOMState: function(led, state) {
                switch (state) {
                    case 'connected':
                        led.removeClass("led_red");
                        led.removeClass("led_orange");
                        led.addClass("led_green");
                        break;
                    case 'not connected':
                        led.removeClass("led_green");
                        led.removeClass("led_orange");
                        led.addClass("led_red");
                        break;
                    case 'connecting':
                        led.removeClass("led_green");
                        led.removeClass("led_red");
                        led.addClass("led_orange");
                        break;
                    default:
                        led.removeClass("led_green");
                        led.removeClass("led_orange");
                        led.addClass("led_red");
                }
            },

            add_entry: function(entry) {
                var rowNode = this.dt.row.add(entry).draw().node();
                if (this.animate) {
                    $( rowNode )
                    .css( 'background-color', '#5cb85c' )
                    .animate( { 'background-color': '', duration: 600 } );
                }
                // this.dt.row.add(entry).draw( false );
                // remove entries
                var numRows = this.dt.rows().count();
                var rowsToRemove = numRows - this._options.tableMaxEntries;
                if (rowsToRemove > 0 && this._options.tableMaxEntries != -1) {
                    //get row indexes as an array
                    var arraySlice = this.dt.rows().indexes().toArray();
                    //get row indexes to remove starting at row 0
                    arraySlice = arraySlice.slice(-rowsToRemove);
                    //remove the rows and redraw the table
                    var rows = this.dt.rows(arraySlice).remove().draw();
                }
            }
        };

        $.livelog = Livelog;
        $.fn.livelog = function(option) {
            var pickerArgs = arguments;

            return this.each(function() {
                var $this = $(this),
                    inst = $this.data('livelog'),
                    options = ((typeof option === 'object') ? option : {});
                if ((!inst) && (typeof option !== 'string')) {
                    $this.data('livelog', new Livelog(this, options));
                } else {
                    if (typeof option === 'string') {
                        inst[option].apply(inst, Array.prototype.slice.call(pickerArgs, 1));
                    }
                }
            });
        };

        $.fn.livelog.constructor = Livelog;

}));

//    ###    ///
//    ###    ///
//    ###    ///
//    ###    ///
//    ###    ///
//    ###    ///

function recursiveInject(result, rules, isNot) {
    if (rules.rules === undefined) { // add to result
        var field = rules.field;
        var value = rules.value;
        var operator_notequal = rules.operator === 'not_equal' ? true : false;
        var negate = isNot ^ operator_notequal;
        value = negate ? '!' + value : value;
        if (result.hasOwnProperty(field)) {
            if (Array.isArray(result[field])) {
                result[field].push(value);
            } else {
                result[field] = [result[field], value];
            }
        } else {
            result[field] = value;
        }
    }
    else if (Array.isArray(rules.rules)) {
        rules.rules.forEach(function(subrules) {
           recursiveInject(result, subrules, isNot ^ rules.not) ;
        });
    }
}

function cleanRules(rules) {
    var res = {};
    recursiveInject(res, rules);
    // clean up invalid and unset
    Object.keys(res).forEach(function(k) {
        var v = res[k];
        if (v === undefined || v === '') {
            delete res[k];
        }
    });
    return res;
}

$(document).ready(function() {
    var qbOptions = {
         plugins: {
             'filter-description' : {
                 mode: 'inline'
             },
             'unique-filter': null,
             'bt-tooltip-errors': null,
         },
         allow_empty: true,
         // lang: {
         //     operators: {
         //         equal: 'show',
         //         in: 'show'
         //     }
         // },
         filters: [],
        rules: {
            condition: 'AND',
            not: false,
            rules: [],
            flags: {
                no_add_group: true,
                condition_readonly: true,
            }
        },
        icons: {
            add_group: 'fa fa-plus-square',
            add_rule: 'fa fa-plus-circle',
            remove_group: 'fa fa-minus-square',
            remove_rule: 'fa fa-minus-circle',
            error: 'fa fa-exclamation-triangle'
        }
    };

    // add filters and rules
    [
        'Attribute.category',
        'Attribute.comment',
        'Attribute.deleted',
        'Attribute.disable_correlation',
        'Attribute.distribution',
        'Attribute.event_id',
        'Attribute.id',
        'Attribute.object_id',
        'Attribute.object_relation',
        'Attribute.sharing_group_id',
        'Attribute.Tag.name',
        'Attribute.timestamp',
        'Attribute.to_ids',
        'Attribute.type',
        'Attribute.uuid',
        'Attribute.value',
        'Event.Org',
        'Event.Orgc',
        'Event.analysis',
        'Event.attribute_count',
        'Event.date',
        'Event.disable_correlation',
        'Event.distribution',
        'Event.event_creator_email',
        'Event.extends_uuid',
        'Event.id',
        'Event.info',
        'Event.locked',
        'Event.org_id',
        'Event.orgc_id',
        'Event.proposal_email_lock',
        'Event.publish_timestamp',
        'Event.published',
        'Event.sharing_group_id',
        'Event.threat_level_id',
        'Event.Tag.name',
        'Event.timestamp',
        'Event.uuid',
        'Org.id',
        'Org.name',
        'Org.uuid',
        'Orgc.id',
        'Orgc.name',
        'Orgc.uuid'
    ].forEach(function(field) {
        var tempFilter = {
            "input": "text",
            "type": "string",
            "operators": [
                "equal",
                "not_equal"
            ],
            "unique": true,
            "id": field,
            "label": field,
            "description": "Perfom strict equality on " + field,
            "validation": {
                "allow_empty_value": true
            }
        };
        qbOptions.filters.push(tempFilter);
    });

    var filterCookie = getCookie('filters');
    var filters = JSON.parse(filterCookie !== undefined && filterCookie !== '' ? filterCookie : "{}");
    var activeFilters = Object.keys(filters)
    var tempRule = [];
    activeFilters.forEach(function(field) {
        var v = filters[field];
        var tmp = {
            field: field,
            id: field,
            value: v
        };
        tempRule.push(tmp);
    });
    qbOptions.rules.rules = tempRule;
    updateFilterButton(activeFilters);

    var $ev = $('#filteringQB');
    var querybuilderTool = $ev.queryBuilder(qbOptions);
    querybuilderTool = querybuilderTool[0].queryBuilder;

    $('#saveFilters').click(function() {
        var rules = querybuilderTool.getRules({ skip_empty: true, allow_invalid: true });
        var result = {};
        recursiveInject(result, rules, false);
        updateFilterButton(Object.keys(result));
        var jres = JSON.stringify(result, null);
        document.cookie = 'filters=' + jres;
        $('#modalFilters').modal('hide');
        livelog.dt
            .clear()
            .draw();
        livelog.fetch_predata();
        livelog.reconnect();
    })

    $('#log-fullscreen').click(function() {
        var $this = $(this);
        var $panel = $('#panelLogTable');
        var isfullscreen = $this.data('isfullscreen');
        if (isfullscreen === undefined || !isfullscreen) {
            $panel.detach().prependTo('#page-wrapper')
            $panel.addClass('liveLogFullScreen');
            $this.data('isfullscreen', true);
        } else {
            $panel.detach().appendTo('#rightCol')
            $panel.removeClass('liveLogFullScreen');
            $this.data('isfullscreen', false);
        }
    });

});

function updateFilterButton(activeFilters) {
    if (activeFilters.length > 0) {
        $('#log-filter').removeClass('btn-default');
        $('#log-filter').addClass('btn-success');
    } else {
        $('#log-filter').removeClass('btn-success');
        $('#log-filter').addClass('btn-default');
    }
}

function getCookie(cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}
