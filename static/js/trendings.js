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
        fill: true
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
        hoverable: true
    }
};

/* FUNCTIONS */
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
function legendFormatter(label, series) {
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
        if (label.length >= 50){
            labelLimited = label.substring(0, 50) + '[...]';
        }   else {
            labelLimited = label;
        }
        return '<div '
                + 'style="font-size:8pt;text-align:inherit;padding:2px;">'
                    + '<a class="tagElem" style="background-color: white; color: black;"> ' + labelLimited
                    + '</a>';
                + '</div>';
    }
}

function generateEmptyAndFillData(data) {
    // formating - Generate empty data
    var toPlot_obj = {};
    var allDates = [];
    var itemMapping = {};
    for (var arr of data) {
        var date = new Date(arr[0]*1000);
        date = new Date(date.valueOf() - date.getTimezoneOffset() * 60000); // center the data around the day
        allDates.push(date);
        var items = arr[1];
        if (items.length > 0) {
            for(var item_arr of items) {
                var count = item_arr[1];
                var itemStr = JSON.stringify(item_arr[0]);
                itemMapping[itemStr] = item_arr[0];
                if(toPlot_obj[itemStr] === undefined)
                    toPlot_obj[itemStr] = {};
                toPlot_obj[itemStr][date] = count;
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
            toPlot.push({label: itemStr, data: data_toPlot, color: itemMapping[itemStr].colour})
        }
    }
    return toPlot;
}

/* UPDATES */

function updatePie(pie, data) {
    var pieID = pie[0];
    var pieWidget = pie[1];
    var itemMapping = {};
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
        toPlot = [];
        for (var itemStr in toPlot_obj) {
            if (toPlot_obj.hasOwnProperty(itemStr)) {
                toPlot.push({label: itemStr, data: toPlot_obj[itemStr], color: itemMapping[itemStr].colour})
            }
        }
    }

    if (!(pieWidget === undefined)) {
        pieWidget.setData(toPlot);
        pieWidget.setupGrid();
        pieWidget.draw();
    } else {
        pieWidget = $.plot(pieID, toPlot, pieChartOption);
        pie.push(pieWidget);
        $(pieID).bind("plothover", function (event, pos, item) {
            if (item) {
                $("#tooltip").html(legendFormatter(item.series.label))
                    .css({top: pos.pageY+5, left: pos.pageX+5})
                    .fadeIn(200);
                } else {
                    $("#tooltip").hide();
                }
            });
    }
}

function updateLine(line, data) {
    lineID = line[0];
    lineWidget = line[1];

    toPlot = generateEmptyAndFillData(data);
    // plot
    if (!(lineWidget === undefined)) {
        lineWidget.setData(toPlot);
        lineWidget.setupGrid();
        lineWidget.draw();
    } else {
        lineWidget = $.plot(lineID, toPlot, lineChartOption);
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
                sightingLineWidget = $.plot("#sightingLine", toPlot, lineChartOptionSight);
            }
        });
}

function updatePieLine(pie, line, url) {
    $.getJSON( url+"?dateS="+parseInt(dateStart.getTime()/1000)+"&dateE="+parseInt(dateEnd.getTime()/1000), function( data ) {
        updatePie(pie, data);
        updateLine(line, data);
    });
}

function dateChanged() {
    dateStart = datePickerWidgetStart.datepicker( "getDate" );
    dateEnd = datePickerWidgetEnd.datepicker( "getDate" );
    updatePieLine(eventPie, eventLine, url_getTrendingEvent);
    updatePieLine(categPie, categLine, url_getTrendingCateg);
    updatePieLine(tagPie, tagLine, url_getTrendingTag);
    updateSignthingsChart();
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

    updatePieLine(eventPie, eventLine, url_getTrendingEvent)
    updatePieLine(categPie, categLine, url_getTrendingCateg)
    updatePieLine(tagPie, tagLine, url_getTrendingTag)
    updateSignthingsChart();


    $("<div id='tooltip'></div>").css({
        position: "absolute",
        display: "none",
    }).appendTo("body");

});
