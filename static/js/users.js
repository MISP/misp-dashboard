var punchcardWidget;
var pieOrgWidget;
var pieApiWidget;
var overtimeWidget;

var div_day;
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

function updateDatePunch() {
    var date = datePickerWidgetPunch.datepicker( "getDate" );
    $.getJSON( url_getUserLogins+"?date="+date.getTime()/1000, function( data ) {
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
function updateDateOvertime() {
    var date = datePickerWidgetOvertime.datepicker( "getDate" );
    var now = new Date();
    if (date.toDateString() == now.toDateString()) {
        date = now;
    } else {
        date.setTime(date.getTime() + (24*60*60*1000-1)); // include data of selected date
    }
    $.getJSON( url_getUserLoginsOvertime+"?date="+parseInt(date.getTime()/1000), function( data ) {
        temp = [];
        var i=0;
        for (item of data) {
            temp.push([new Date(item[0]*1000), item[1]]);
        }
        toPlot = [{label: 'Login overtime', data: temp}];
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

});
