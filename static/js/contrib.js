/* CONFIG */
var allOrg = [];
var datatableTop;
var datatableFame;
var optionsLineChart = {
    series: {
            shadowSize: 0 ,
            lines: {
                fill: true,
                fillColor: {
                    colors: [ { opacity: 1 }, { opacity: 0.1 } ]
                }
            }
    },
    points: { show: true },
    lines: { show: true, fill: true },
    grid: {
        tickColor: "#dddddd",
        borderWidth: 0
    },
    legend: {
        show: true,
        position: "nw"
    }
};
var optionDatatable_light = {
    responsive: true,
    searching: false,
    ordering: false,
    scrollY:        '30vh',
    scrollCollapse: true,
    paging:         false,
    "language": {
        "lengthMenu": "",
        "info": "",
        "infoFiltered": "",
        "infoEmpty": "",
    },
    "info": false,
};
var optionDatatable_top = jQuery.extend({}, optionDatatable_light)
var optionDatatable_last = jQuery.extend({}, optionDatatable_light)
var optionDatatable_fame = jQuery.extend({}, optionDatatable_light)
optionDatatable_fame.scrollY = '50vh';

var optionDatatable_Categ = {
    responsive: true,
    searching: true,
    scrollY:        '39vh',
    scrollCollapse: true,
    paging:         false,
    "info": false,
};

var typeaheadOption = {
    source: function (query, process) {
        if (allOrg.length == 0) { // caching
            return $.getJSON(url_getAllOrg, function (data) {
                    allOrg = data;
                    return process(data);
            });
        } else {
            return process(allOrg);
        }
    },
    updater: function(item) {
        $('#orgText').text(item);
    }
}

/* FUNCTIONS */
function getRankIcon(rank, size) {
    rankLogoPath = url_baseRankLogo+rank+'.png';
    var img = document.createElement('img');
    img.src = rankLogoPath;
    if(size == undefined) {
        img.height = 26;
        img.width = 26;
    } else {
        img.height = size;
        img.width = size;
    }
    return img.outerHTML;
}

function addToTableFromJson(datatable, url) {
    $.getJSON( url, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                i+1,
                getRankIcon(row.rank),
                row.logo_path,
                row.org
            ];
            datatable.row.add(to_add);
        }
        datatable.draw();
    });
}




$(document).ready(function() {
    $('#orgName').typeahead(typeaheadOption);
    $('#orgRankDiv').html(getRankIcon(8, 50));
    $('#orgNextRankDiv').html(getRankIcon(9, 50));
    $('#orgText').text(currOrg);
    datatableTop = $('#topContribTable').DataTable(optionDatatable_top);
    datatableFame = $('#fameTable').DataTable(optionDatatable_fame);
    datatableCateg = $('#categTable').DataTable(optionDatatable_Categ);
    datatableLast = $('#lastTable').DataTable(optionDatatable_last);
    // top contributors
    $.getJSON(url_getTopContributor , function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                i+1,
                getRankIcon(row.rank),
                row.logo_path,
                row.org
            ];
            datatableTop.row.add(to_add);
        }
        datatableTop.draw();
    });

    // hall of fame
    $.getJSON( url_getTopContributor, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                i+1,
                getRankIcon(row.rank),
                row.logo_path,
                row.org
            ];
            datatableFame.row.add(to_add);
        }
        datatableFame.draw();
    });

    $.getJSON( url_getTopContributor, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                i+1,
                getRankIcon(row.rank),
                row.logo_path,
                row.org
            ];
            datatableLast.row.add(to_add);
        }
        datatableLast.draw();
    });

    $.getJSON( url_getCategPerContrib, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                i+1,
                getRankIcon(row.rank),
                row.logo_path,
                row.org,
                row.network_activity,
                row.payload_delivery,
                row.others
            ];
            datatableCateg.row.add(to_add);
        }
        datatableCateg.draw();
    });
    // top 5 contrib overtime
    $.getJSON( url_getTop5Overtime, function( data ) {
        var plotLineChart = $.plot("#divTop5Overtime", data, optionsLineChart);
    });
});
