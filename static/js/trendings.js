function dateChanged() {
    var date = datePickerWidget.datepicker( "getDate" );
    console.log(date);
}

$(document).ready(function () {

    var datePickerOptions = {
        showOn: "button",
        maxDate: 0,
        buttonImage: urlIconCalendar,
        buttonImageOnly: true,
        buttonText: "Select date",
        showAnim: "slideDown",
        onSelect: dateChanged
    };
    var datePickerOptions = jQuery.extend({}, datePickerOptions);
    datePickerWidget = $( "#datepicker" );
    datePickerWidget.datepicker(datePickerOptions);
    datePickerWidget.datepicker("setDate", new Date());

});
