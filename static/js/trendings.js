/* VARS */
var dateStart;
var dateEnd;
var eventPie = ["#eventPie"];
var eventLine = ["#eventLine"];
var categPie = ["#categPie"];
var categLine = ["#categLine"];
var tagPie = ["#tagPie"];
var tagLine = ["#tagLine"];
var sightingEventPieWidget;
var sightingCategLineWidget;

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
        steps: true,
        fill: true
    },
    xaxis: {
        mode: "time",
        minTickSize: [1, "day"],
    },
    legend: {
        show: false,
    }
};
var pieChartOption = {
    series: {
        pie: {
            innerRadius: 0.2,
            show: true,
            label: {
                show: true,
                radius: 1,
                formatter: innerPieLabelFormatter,
            }
        }
    },
    legend: {
        show: true,
        labelFormatter: legendFormatter
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
        // transforming true into "true", removing unwanted "
        var jsonLabel = label.replace(/\"/g, "").replace(/True/g, "\"True\"").replace(/False/g, "\"False\"").replace(/\'/g, "\"")
        jsonLabel = JSON.parse(jsonLabel);
        var backgroundColor = jsonLabel.colour;
        var color = getTextColour(backgroundColor.substring(1,6));;
        var labelText = jsonLabel.name;
        return '<div '
               + 'style="font-size:8pt;text-align:inherit;padding:2px;">'
                   + '<a class="tagElem" style="background-color: '+ backgroundColor + ';'
                   + 'color: ' + color + ';"> ' + labelText + '</a>'
               + '</div>';
    } catch(err) {
        return '<div '
            + '<a class="tagElem"> ' + label
            + '</a>';
    }
}

function updatePie(pie, data) {
    pieID = pie[0];
    pieWidget = pie[1];
    if (data === undefined || data.length == 0 || (data[0] == 0 && data[1] == 0)) {
        toPlot = [{ label: 'No data', data: 100 }];
    } else {
        toPlot_obj = {}
        for (var arr of data) {
            var date = arr[0];
            var items = arr[1]
            for(var item_arr of items) {
                var item = item_arr[0];
                var count = item_arr[1];
                if(toPlot_obj[item] === undefined)
                    toPlot_obj[item] = 0;
                toPlot_obj[item] += count;
            }
        }
        toPlot = [];
        for (var item in toPlot_obj) {
            if (toPlot_obj.hasOwnProperty(item)) {
                toPlot.push({label: item, data: toPlot_obj[item]})
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
    }
}

function updateLine(line, data) {
    lineID = line[0];
    lineWidget = line[1];

    // formating - Generate empty data
    toPlot_obj = {};
    allDates = [];
    for (var arr of data) {
        var date = new Date(arr[0]*1000);
        allDates.push(date);
        var items = arr[1];
        if (items.length > 0) {
            for(var item_arr of items) {
                var count = item_arr[1];
                var item = item_arr[0]
                if(toPlot_obj[item] === undefined)
                    toPlot_obj[item] = {};
                toPlot_obj[item][date] = count;
            }
        }
    }
    toPlot = []
    for (var item in toPlot_obj) {
        if (toPlot_obj.hasOwnProperty(item)) {
            data_toPlot = []
            for (var curDate of allDates) {
                if (toPlot_obj[item].hasOwnProperty(curDate)) {
                    data_toPlot.push([curDate, toPlot_obj[item][curDate]])
                } else {
                    data_toPlot.push([curDate, 0])
                }
            }
            toPlot.push({label: item, data: data_toPlot})
        }
    }
    // plot
    if (!(lineWidget === undefined)) {
        lineWidget.setData(toPlot);
        lineWidget.setupGrid();
        lineWidget.draw();
    } else {
        lineWidget = $.plot(lineID, toPlot, lineChartOption);
        line.push(lineWidget);
    }
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
    updatePieLine(eventPie, eventLine, url_getTrendingEvent)
    updatePieLine(categPie, categLine, url_getTrendingCateg)
    updatePieLine(tagPie, tagLine, url_getTrendingTag)
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

});
