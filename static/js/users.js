var punchcardWidget;
var pieOrgWidget;
var pieApiWidget;
var overtimeWidget;
var div_day;
var allOrg;

var typeaheadOption_punch = {
    source: function (query, process) {
        if (allOrg === undefined) { // caching
            return $.getJSON(url_getTypeaheadData, function (orgs) {
                    allOrg = orgs;
                    return process(orgs);
            });
        } else {
            return process(allOrg);
        }
    },
    updater: function(org) {
        updateDatePunch(undefined, undefined, org);
    }
}
var typeaheadOption_overtime = {
    source: function (query, process) {
        if (allOrg === undefined) { // caching
            return $.getJSON(url_getTypeaheadData, function (orgs) {
                    allOrg = orgs;
                    return process(orgs);
            });
        } else {
            return process(allOrg);
        }
    },
    updater: function(org) {
        updateDateOvertime(undefined, undefined, org);
    }
}

function legendFormatter(label, series) {
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

function highlight_punchDay() {
    if (!(div_day === undefined)) {
        div_day.removeClass('highlightDay');
    }

    var curDay = datePickerWidgetPunch.datepicker( "getDate" ).getDay();
    if (curDay == 7)
        curDay = 0;
    div_day = $('[data-daynum="'+curDay+'"]');
    div_day.addClass('highlightDay')
}

function updateDatePunch(ignore1, igonre2, org) { //date picker sets ( String dateText, Object inst )
    var date = datePickerWidgetPunch.datepicker( "getDate" );
    if (org === undefined){
        $('#typeaheadPunch').attr('placeholder', "Enter an organization");
        var url = url_getUserLogins+"?date="+date.getTime()/1000;
    } else {
        $('#typeaheadPunch').attr('placeholder', org);
        var url = url_getUserLogins+"?date="+date.getTime()/1000+"&org="+org;
    }
    $.getJSON(url, function( data ) {
        if (!(punchcardWidget === undefined)) {
            punchcardWidget.settings.data = data;
            punchcardWidget.refresh();
            highlight_punchDay();
        } else {
            punchcardWidget = $('#punchcard').punchcard({
                data: data,
                singular: 'login',
                plural: 'logins',
                timezones: ['local'],
                timezoneIndex:0
            });
            punchcardWidget = punchcardWidget.data("plugin_" + "punchcard");
            highlight_punchDay();
        }
    });
}
function updateDatePieOrg() {
    var date = datePickerWidgetOrg.datepicker( "getDate" );
    $.getJSON( url_getTopOrglogin+"?date="+date.getTime()/1000, function( data ) {
        toPlot = [];
        for (item of data) { toPlot.push({ label: item[0], data: item[1] }); }
        if (toPlot.length == 0) {
            toPlot = [{ label: 'No data', data: 100 }];
        }
        if (!(pieOrgWidget === undefined)) {
            pieOrgWidget.setData(toPlot);
            pieOrgWidget.setupGrid();
            pieOrgWidget.draw();
        } else {
            pieOrgWidget = $.plot('#pieOrg', toPlot, {
                series: {
                    pie: {
                        innerRadius: 0.5,
                        show: true
                    }
                },
                grid: {
                    hoverable: true
                }
            });
            $('#pieOrg').bind("plothover", function (event, pos, item) {
                if (item) {
                    $("#tooltip").html(legendFormatter(item.series.label))
                        .css({top: pos.pageY+5, left: pos.pageX+5})
                        .fadeIn(200);
                } else {
                    $("#tooltip").hide();
                }
            });
        }
    });
}
function updateDatePieApi() {
    var date = datePickerWidgetApi.datepicker( "getDate" );
    $.getJSON( url_getLoginVSCOntribution+"?date="+date.getTime()/1000, function( data ) {
        toPlot = [
            {label: 'Login with contribution during the day', data: data[0], color: '#4da74d' },
            {label: 'Login without contribution during the day', data:data[1], color: '#cb4b4b' }
        ];
        if (data[0] == 0 && data[1] == 0) {
            toPlot = [{ label: 'No data', data: 100 }];
        }

        if (!(pieApiWidget === undefined)) {
            pieApiWidget.setData(toPlot);
            pieApiWidget.setupGrid();
            pieApiWidget.draw();
        } else {
            pieApiWidget = $.plot('#pieApi', toPlot, {
                series: {
                    pie: {
                        innerRadius: 0.5,
                        show: true
                    }
                }
            });
        }
    });
}
function updateDateOvertime(ignore1, igonre2, org) { //date picker sets ( String dateText, Object inst )
    var date = datePickerWidgetOvertime.datepicker( "getDate" );
    var now = new Date();
    if (date.toDateString() == now.toDateString()) {
        date = now;
    } else {
        date.setTime(date.getTime() + (24*60*60*1000-1)); // include data of selected date
    }
    if (org === undefined){
        var url = url_getUserLoginsAndContribOvertime+"?date="+parseInt(date.getTime()/1000)
        $('#typeaheadOvertime').attr('placeholder', "Enter an organization");
    } else {
        var url = url_getUserLoginsAndContribOvertime+"?date="+parseInt(date.getTime()/1000)+"&org="+org;
        $('#typeaheadOvertime').attr('placeholder', org);
    }
    $.getJSON( url, function( data ) {
        data_log = data['login'];
        data_contrib = data['contrib'];
        temp_log = [];
        var i=0;
        for (item of data_log) {
            var date = new Date(item[0]*1000);
            date = new Date(date.valueOf() - date.getTimezoneOffset() * 60000); // center the data around the day
            temp_log.push([date, item[1]]);
        }
        temp_contrib= [];
        var i=0;
        for (item of data_contrib) {
            var date = new Date(item[0]*1000);
            date = new Date(date.valueOf() - date.getTimezoneOffset() * 60000); // center the data around the day
            temp_contrib.push([date, item[1]]);
        }
        toPlot = [{label: 'Login', data: temp_log}, {label: 'Contribution', data: temp_contrib}];
        if (!(overtimeWidget === undefined)) {
            overtimeWidget.setData(toPlot);
            overtimeWidget.setupGrid();
            overtimeWidget.draw();
        } else {
            overtimeWidget = $.plot('#lineChart', toPlot, {
                lines: {
                    show: true,
                    steps: true,
                    fill: true
                },
                xaxis: {
                    mode: "time",
                    minTickSize: [1, "day"],
                }
            });
        }
    });

}

$(document).ready(function () {

    var datePickerOptions = {
        showOn: "button",
        maxDate: 0,
        buttonImage: urlIconCalendar,
        buttonImageOnly: true,
        buttonText: "Select date",
        showAnim: "slideDown"
    };
    // punch
    var datePickerOptionsPunch = jQuery.extend({}, datePickerOptions);
    datePickerOptionsPunch['onSelect'] = updateDatePunch;
    datePickerWidgetPunch = $( "#datepickerPunch" );
    datePickerWidgetPunch.datepicker(datePickerOptionsPunch);
    datePickerWidgetPunch.datepicker("setDate", new Date());
    // org login
    var datePickerOptionsOrg = jQuery.extend({}, datePickerOptions);
    datePickerOptionsOrg['onSelect'] = updateDatePieOrg;
    datePickerWidgetOrg = $( "#datepickerOrgLogin" );
    datePickerWidgetOrg.datepicker(datePickerOptionsOrg);
    datePickerWidgetOrg.datepicker("setDate", new Date());
    // api
    var datePickerOptionsApi = jQuery.extend({}, datePickerOptions);
    datePickerOptionsApi['onSelect'] = updateDatePieApi;
    datePickerWidgetApi = $( "#datepickerApi" );
    datePickerWidgetApi.datepicker(datePickerOptionsApi);
    datePickerWidgetApi.datepicker("setDate", new Date());
    // overtime
    var datePickerOptionsOvertime = jQuery.extend({}, datePickerOptions);
    datePickerOptionsOvertime['onSelect'] = updateDateOvertime;
    datePickerWidgetOvertime = $( "#datepickerOvertimeLogin" );
    datePickerWidgetOvertime.datepicker(datePickerOptionsOvertime);
    datePickerWidgetOvertime.datepicker("setDate", new Date());

    updateDatePunch();
    updateDatePieOrg();
    updateDatePieApi();
    updateDateOvertime();

    $('#typeaheadPunch').typeahead(typeaheadOption_punch);
    $('#typeaheadOvertime').typeahead(typeaheadOption_overtime);

    $("<div id='tooltip'></div>").css({
        position: "absolute",
        display: "none",
    }).appendTo("body");

});
