/* VARS */
var dateStart;
var dateEnd;
var eventPie = ["#eventPie"];
var eventLine = ["#eventLine"];
var categPie = ["#categPie"];
var categLine = ["#categLine"];
var tagPie = ["#tagPie"];
var tagLine = ["#tagLine"];
var sightingLineWidget;
var discLine = ["#discussionLine"];
var timeline;
var allData;
var globalColorMapping = {};

/* OPTIONS */
var datePickerOptions = {
    showOn: "button",
    maxDate: 0,
    buttonImage: urlIconCalendar,
    buttonImageOnly: true,
    buttonText: "Select date",
    showAnim: "slideDown",
    onSelect: dateChanged
};
var lineChartOption = {
    lines: {
        show: true,
    },
    points: { show: true },
    xaxis: {
        mode: "time",
        minTickSize: [1, "day"],
    },
    legend: { show: false },
    grid: {
        hoverable: true
    }
};
var pieChartOption = {
    series: {
        pie: {
            innerRadius: 0.2,
            show: true,
            radius: 100,
            stroke: { color: 'black' },
            label: {
                show: true,
                radius: 6/10,
                formatter: innerPieLabelFormatter,
            }
        }
    },
    legend: {
        show: true,
        labelFormatter: legendFormatter
    },
    grid: {
        hoverable: true,
        clickable: true
    }
};
var typeaheadOption_event = {
    source: function (query, process) {
        if (allData === undefined) { // caching
            return $.getJSON(url_getTypeaheadData, function (data) {
                    allData = data;
                    return process(data.TRENDINGS_EVENTS);
            });
        } else {
            return process(allData.TRENDINGS_EVENTS);
        }
    },
    updater: function(theevent) {
        updateLineForLabel(eventLine, theevent, undefined, url_getTrendingEvent);
    }
}
var typeaheadOption_categ = {
    source: function (query, process) {
        if (allData  === undefined) { // caching
            return $.getJSON(url_getTypeaheadData, function (data) {
                    allData = data;
                    return process(data.TRENDINGS_CATEGS);
            });
        } else {
            return process(allData.TRENDINGS_CATEGS);
        }
    },
    updater: function(categ) {
        updateLineForLabel(categLine, categ, undefined, url_getTrendingCateg);
    }
}
var typeaheadOption_tag = {
    source: function (query, process) {
        if (allData === undefined) { // caching
            return $.getJSON(url_getTypeaheadData, function (data) {
                    allData = data;
                    return process(data.TRENDINGS_TAGS);
            });
        } else {
            return process(allData.TRENDINGS_TAGS);
        }
    },
    updater: function(tag) {
        updateLineForLabel(tagLine, tag, undefined, url_getTrendingTag);
    }
}
var timeline_option = {
    groupOrder: 'content',
    maxHeight: '94vh',
    verticalScroll: true,
    horizontalScroll: true,
    zoomKey: 'ctrlKey',
};


/* FUNCTIONS */
function getColor(label) {
    try {
        return globalColorMapping[label];
    } catch(err) {
        return undefined;
    }

}

function innerPieLabelFormatter(label, series) {
    var count = series.data[0][1];
    return '<div '
           + 'style="font-size:8pt;text-align:inherit;padding:2px;">'
               + '<a class="tagElem" style="background-color: '+ 'white' + ';'
               + 'color: ' + 'black' + ';"> ' + count + '</a>'
           + '</div>';
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

// If json (from tag), only retreive the name> otherwise return the supplied arg.
function getOnlyName(potentialJson) {
    try {
        jsonLabel = JSON.parse(potentialJson);
        return jsonLabel.name;
    } catch(err) {
        return potentialJson;
    }
}

function legendFormatter(label) {
    try {
        jsonLabel = JSON.parse(label);
        var backgroundColor = jsonLabel.colour;
        var color = getTextColour(backgroundColor.substring(1,6));;
        var labelText = jsonLabel.name;
        return '<div '
               + 'style="font-size:8pt;text-align:inherit;padding:2px;">'
                   + '<a class="tagElem" style="background-color: '+ backgroundColor + ';'
                   + 'color: ' + color + ';"> ' + labelText + '</a>'
               + '</div>';
    } catch(err) {
        // removing unwanted "
        var label = label.replace(/\\"/g, "").replace(/\"/g, "");
        // limiting size
        if (label.length >= 40){
            labelLimited = label.substring(0, 40) + '[...]';
        }   else {
            labelLimited = label;
        }
        return '<div '
                + 'style="font-size:8pt;text-align:inherit;padding:2px;">'
                    + '<a class="tagElem" title="'+label+'" style="background-color: white; color: black;"> ' + labelLimited
                    + '</a>';
                + '</div>';
    }
}

function generateEmptyAndFillData(data, specificLabel, colorMapping) {
    // formating - Generate empty data
    var toPlot_obj = {};
    var allDates = [];
    for (var arr of data) {
        var date = new Date(arr[0]*1000);
        date = new Date(date.valueOf() - date.getTimezoneOffset() * 60000); // center the data around the day
        allDates.push(date);
        var items = arr[1];
        if (items.length > 0) {
            for(var item_arr of items) {
                var count = item_arr[1];
                var itemStr = JSON.stringify(item_arr[0]);
                if (specificLabel === undefined || specificLabel == item_arr[0]) { // no tag
                    if(toPlot_obj[itemStr] === undefined)
                        toPlot_obj[itemStr] = {};
                    toPlot_obj[itemStr][date] = count;
                } else if (specificLabel == item_arr[0].name) { // tag
                    if(toPlot_obj[itemStr] === undefined)
                        toPlot_obj[itemStr] = {};
                    toPlot_obj[itemStr][date] = count;
                } else if (specificLabel == itemStr.substring(1, itemStr.length-1)) { // tag from click (countain { and }, need to supress it)
                    if(toPlot_obj[itemStr] === undefined)
                        toPlot_obj[itemStr] = {};
                    toPlot_obj[itemStr][date] = count;
                }
            }
        }
    }
    toPlot = []
    for (var itemStr in toPlot_obj) {
        if (toPlot_obj.hasOwnProperty(itemStr)) {
            data_toPlot = []
            for (var curDate of allDates) {
                if (toPlot_obj[itemStr].hasOwnProperty(curDate)) {
                    data_toPlot.push([curDate, toPlot_obj[itemStr][curDate]])
                } else {
                    data_toPlot.push([curDate, 0])
                }
            }
            if (colorMapping === undefined) {
                //try to get color, else no color
                var colorCode = getColor(itemStr);
                if (!( colorCode === undefined)) {
                    toPlot.push({label: itemStr, data: data_toPlot, color: colorCode})
                } else {
                    toPlot.push({label: itemStr, data: data_toPlot})
                }
            } else {
                try {
                    var color = colorMapping[itemStr].colour;
                    toPlot.push({label: itemStr, data: data_toPlot, color: color})
                } catch(err) {
                    // ignore, only shows data displayed in the pie chart
                }
            }
        }
    }
    return toPlot;
}

function compareObj(a,b) {
  if (a.data < b.data)
    return -1;
  if (a.data > b.data)
    return 1;
  return 0;
}
/* UPDATES */

// return the color maping: label->color
function updatePie(pie, line, data, url) {
    var pieID = pie[0];
    var pieWidget = pie[1];
    var itemMapping = {};
    var colorMapping = {};
    if (data === undefined || data.length == 0 || (data[0] == 0 && data[1] == 0)) {
        toPlot = [{ label: 'No data', data: 100 }];
    } else {
        toPlot_obj = {}
        for (var arr of data) {
            var date = arr[0];
            var items = arr[1]
            for(var item_arr of items) {
                var itemStr = JSON.stringify(item_arr[0]);
                itemMapping[itemStr] = item_arr[0];
                var count = item_arr[1];
                if(toPlot_obj[itemStr] === undefined)
                    toPlot_obj[itemStr] = 0;
                toPlot_obj[itemStr] += count;
            }
        }
        if (Object.keys(toPlot_obj).length == 0) { // no data
            toPlot = [{ label: 'No data', data: 100 }];
        } else {
            toPlot = [];
            for (var itemStr in toPlot_obj) {
                if (toPlot_obj.hasOwnProperty(itemStr)) {
                    var itemColor = itemMapping[itemStr].colour
                    colorMapping[itemStr] = itemColor;
                    toPlot.push({label: itemStr, data: toPlot_obj[itemStr], color: itemColor})
                }
            }
        }
        toPlot.sort(compareObj).reverse();
        var maxNum = $('#num_selector').val();
        toPlot = toPlot.slice(0,maxNum); // take at max 12 elements
    }
    if (!(pieWidget === undefined)) {
        pieWidget.setData(toPlot);
        pieWidget.setupGrid();
        pieWidget.draw();
        // fill colorMapping
        for (item of pieWidget.getData()) {
            colorMapping[item.label] = {colour: item.color};
        }
    } else {
        pieWidget = $.plot(pieID, toPlot, pieChartOption);
        pie.push(pieWidget);
        // Hover
        $(pieID).bind("plothover", function (event, pos, item) {
            if (item) {
                $("#tooltip").html(legendFormatter(item.series.label))
                    .css({top: pos.pageY+5, left: pos.pageX+5})
                    .fadeIn(200);
            } else {
                $("#tooltip").hide();
            }
        });
        // Click
        $(pieID).bind("plotclick", function(event, pos, obj) {
            if (!obj) { return; }
            var specificLabel = obj.series.label;
            colorMapping[specificLabel] = {};
            colorMapping[specificLabel] =  { colour: obj.series.color };
            updateLineForLabel(line, specificLabel.substring(1, specificLabel.length-1), colorMapping, url);
        });
        for (item of pieWidget.getData()) {
            colorMapping[item.label] = {colour: item.color};
        }
    }
    return colorMapping;
}

function updateLine(line, data, chartOptions, specificLabel, colorMapping) {
    lineID = line[0];
    lineWidget = line[1];
    toPlot = generateEmptyAndFillData(data, specificLabel, colorMapping);
    // plot
    if (!(lineWidget === undefined)) {
        lineWidget.setData(toPlot);
        lineWidget.setupGrid();
        lineWidget.draw();
    } else {
        if (chartOptions === undefined) {
            chartOptions = lineChartOption;
        }
        lineWidget = $.plot(lineID, toPlot, chartOptions);
        line.push(lineWidget);
        $(lineID).bind("plothover", function (event, pos, item) {
            if (item) {
                $("#tooltip").html(legendFormatter(item.series.label))
                    .css({top: item.pageY+5, left: item.pageX+5})
                    .fadeIn(200);
                } else {
                    $("#tooltip").hide();
                }
        });
    }
}

function updateSignthingsChart() {
        $.getJSON( url_getTrendingSightings+"?dateS="+parseInt(dateStart.getTime()/1000)+"&dateE="+parseInt(dateEnd.getTime()/1000), function( data ) {
            var toPlot_obj = {};
            toPlot_obj['Sightings'] = [];
            toPlot_obj['False positive'] = [];
            var allDates = [];
            for (var arr of data) {
                var date = new Date(arr[0]*1000);
                date = new Date(date.valueOf() - date.getTimezoneOffset() * 60000); // center the data around the day
                allDates.push(date);
                var items = arr[1];
                var sight = items.sightings;
                var fp = items.false_positive;
                toPlot_obj['Sightings'].push([date, sight]);
                toPlot_obj['False positive'].push([date, -fp]);
            }
            toPlot = []
            toPlot.push({label: 'Sightings', data: toPlot_obj['Sightings'], color: '#4da74d'})
            toPlot.push({label: 'False positive', data: toPlot_obj['False positive'], color: '#cb4b4b'})

            if (!(sightingLineWidget === undefined)) {
                sightingLineWidget.setData(toPlot);
                sightingLineWidget.setupGrid();
                sightingLineWidget.draw();
            } else {
                var lineChartOptionSight = jQuery.extend(true, {}, lineChartOption);
                lineChartOptionSight['legend']['show'] = true;
                lineChartOptionSight['legend']['position'] = 'nw';
                lineChartOptionSight['grid'] = {};
                lineChartOptionSight['lines']['fill'] = true;
                sightingLineWidget = $.plot("#sightingLine", toPlot, lineChartOptionSight);
            }
        });
}

function updateLineForLabel(line, specificLabel, colorMapping, url) {
    $.getJSON( url+"?dateS="+parseInt(dateStart.getTime()/1000)+"&dateE="+parseInt(dateEnd.getTime()/1000)+"&specificLabel="+specificLabel, function( data ) {
        updateLine(line, data, undefined, specificLabel, colorMapping);
    });
}

function updatePieLine(pie, line, url) {
    $.getJSON( url+"?dateS="+parseInt(dateStart.getTime()/1000)+"&dateE="+parseInt(dateEnd.getTime()/1000), function( data ) {
        var colorMapping = updatePie(pie, line, data, url);
        for (var item in colorMapping) {
            if (colorMapping.hasOwnProperty(item) && colorMapping[item] != undefined) {
                globalColorMapping[item] = colorMapping[item].colour;
            }
        }
        updateLine(line, data, undefined, undefined, colorMapping);
    });
}

function updateDisc() {
    var lineChartOptionDisc = jQuery.extend(true, {}, lineChartOption);
    lineChartOptionDisc['legend']['show'] = true;
    lineChartOptionDisc['legend']['position'] = 'nw';
    lineChartOptionDisc['lines']['fill'] = true;
    $.getJSON( url_getTrendingDisc+"?dateS="+parseInt(dateStart.getTime()/1000)+"&dateE="+parseInt(dateEnd.getTime()/1000), function( data ) {
        updateLine(discLine, data, lineChartOptionDisc);
    });
}

var items_timeline = [];
function updateTimeline() {
    var selected = $( "#timeline_selector" ).val();
    $.getJSON( url_getGenericTrendingOvertime+"?dateS="+parseInt(dateStart.getTime()/1000)+"&dateE="+parseInt(dateEnd.getTime()/1000)+"&choice="+selected, function( data ) {
        items_timeline = [];
        var groups = new vis.DataSet();
        var dico_groups = {};
        var i = 1;
        var g = 1;
        for (var obj of data) {
            var index = dico_groups[obj.name];
            if (index == undefined) { // new group
                index = groups.add({id: g, content: legendFormatter(obj.name)});
                dico_groups[obj.name] = g;
                g++;
            }
            items_timeline.push({
                id: i,
                content: getOnlyName(obj.name),
                title: obj.name,
                start: obj.start*1000,
                end: obj.end*1000,
                group: dico_groups[obj.name]
            });
            i++;
        }
        items_timeline = new vis.DataSet(items_timeline);
        if (timeline === undefined) { // create timeline
            timeline = new vis.Timeline(document.getElementById('timeline'));
            // set listener for tooltip
            timeline.on('doubleClick', function (properties) {
                var type = $( "#timeline_selector" ).val();
                var itemValue = items_timeline.get(properties.item).content;
                if (type.localeCompare('events') == 0 || type.localeCompare('tags') == 0) { // Do not open a tab for categ
                    window.open(url_misp+'/'+type+'/index/searchall:'+itemValue, '_blank'); // as we do not have index for the moment, search it
                }
            });
        }
        var dateEndExtended = new Date(dateEnd).setDate(dateEnd.getDate()+1); // dateEnd+1
        timeline_option.start = dateStart;
        timeline_option.end = dateEndExtended;
        timeline.setOptions(timeline_option);
        timeline.setGroups(groups);
        timeline.setItems(items_timeline);
    });
}

function dateChanged() {
    dateStart = datePickerWidgetStart.datepicker( "getDate" );
    dateEnd = datePickerWidgetEnd.datepicker( "getDate" );
    updatePieLine(eventPie, eventLine, url_getTrendingEvent);
    updatePieLine(categPie, categLine, url_getTrendingCateg);
    updatePieLine(tagPie, tagLine, url_getTrendingTag);
    updateSignthingsChart();
    updateDisc();
    updateTimeline();
}

$(document).ready(function () {

    datePickerWidgetStart = $( "#datepickerStart" ).datepicker(datePickerOptions);
    var lastWeekDate = new Date();
    lastWeekDate.setDate(lastWeekDate.getDate()-7);
    datePickerWidgetStart.datepicker("setDate", lastWeekDate);
    dateStart = datePickerWidgetStart.datepicker( "getDate" );
    datePickerWidgetEnd = $( "#datepickerEnd" ).datepicker(datePickerOptions);
    datePickerWidgetEnd.datepicker("setDate", new Date());
    dateEnd = datePickerWidgetEnd.datepicker( "getDate" );

    $('#typeaheadEvent').typeahead(typeaheadOption_event);
    $('#typeaheadCateg').typeahead(typeaheadOption_categ);
    $('#typeaheadTag').typeahead(typeaheadOption_tag);

    updatePieLine(eventPie, eventLine, url_getTrendingEvent)
    updatePieLine(categPie, categLine, url_getTrendingCateg)
    updatePieLine(tagPie, tagLine, url_getTrendingTag)
    updateSignthingsChart();
    updateDisc();
    updateTimeline();

    $( "#num_selector" ).change(function() {
        var sel = parseInt($( this ).val());
        var maxNum = sel;
        window.location.href = url_currentPage+'?maxNum='+maxNum;
    });

    $( "#timeline_selector" ).change(function() {
        updateTimeline();
    });

    $("<div id='tooltip'></div>").css({
        position: "absolute",
        display: "none",
    }).appendTo("body");
});
