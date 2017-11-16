/* VARS */
var date;
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
    }
};
var pieChartOption = {
    series: {
        pie: {
            innerRadius: 0.5,
            show: true
        }
    }
};

/* FUNCTIONS */

function updatePie(pie, data) {
    pieID = pie[0];
    pieWidget = pie[1];
    if (data === undefined || data.length == 0 || (data[0] == 0 && data[1] == 0)) {
        toPlot = [{ label: 'No data', data: 100 }];
    } else {
        toPlot = [];
        for (item of data) {
            toPlot.push({label: item[0], data: item[1]});
        }
    }
    console.log(toPlot);
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
    temp = [];
    var i=0;
    for (item of data) {
        temp.push([new Date(item[0]*1000), item[1]]);
    }
    data = {label: 'Overtime', data: temp}
    if (!(lineWidget === undefined)) {
        lineWidget.setData(toPlot);
        lineWidget.draw();
    } else {
        lineWidget = $.plot(lineID, [data], lineChartOption);
        line.push(lineWidget);
    }
}

function updatePieLine(pie, line, url) {
    // format date
    // var now = new Date();
    // if (date.toDateString() == now.toDateString()) {
    //     date = now;
    // } else {
    //     date.setTime(date.getTime() + (24*60*60*1000-1)); // include data of selected date
    // }
    $.getJSON( url+"?date="+parseInt(date.getTime()/1000), function( data ) {
        updatePie(pie, data[0][1]);
        updateLine(line, data);
    });
}

function dateChanged() {
    date = datePickerWidget.datepicker( "getDate" );
    updatePieLine(eventPie, eventLine, url_getTrendingEvent)
    updatePieLine(categPie, categLine, url_getTrendingCateg)
    updatePieLine(tagPie, tagLine, url_getTrendingTag)
}

$(document).ready(function () {

    datePickerWidget = $( "#datepicker" ).datepicker(datePickerOptions);
    datePickerWidget.datepicker("setDate", new Date());
    date = datePickerWidget.datepicker( "getDate" );

    updatePieLine(eventPie, eventLine, url_getTrendingEvent)
    updatePieLine(categPie, categLine, url_getTrendingCateg)
    updatePieLine(tagPie, tagLine, url_getTrendingTag)

});
