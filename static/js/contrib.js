/* GLOB VAR */
var allOrg = [];
var datatableTop;
var datatableFame;

/* CONFIG */
var maxRank = 16;
var popOverOption = {
    trigger: "hover",
    html: true,
    placement: 'bottom',
    content: generateRankingSheet()
}
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
    scrollY:        '38vh',
    "scrollX": true,
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
    updater: function(org) {
        updateProgressHeader(org);
    }
}

/* FUNCTIONS */
function getRankIcon(rank, size, header) {
    if (rank > 16) {
        rankLogoPath = url_baseRankLogo+0+'.png';
    } else {
        rankLogoPath = url_baseRankLogo+rank+'.png';
    }
    var img = document.createElement('img');
    img.src = rankLogoPath;
    if(size == undefined) {
        img.height = 26;
        img.width = 26;
    } else {
        if (header) {
            img.height = size;
            img.width = size;
            img.style.position = 'absolute';
            img.style.top = '0';
            img.style.bottom = '0';
            img.style.margin = 'auto';
            img.style.left = '0px';
        } else {
            img.height = size;
            img.width = size;
        }
    }
    return img.outerHTML;
}
function generateRankingSheet(rank, rankDec, stepPnt, pnt, Rpnt) {
    var Cpnt = pnt - stepPnt;
    var Tpnt = Cpnt + Rpnt;
    var OuterDiv = document.createElement('div');
    var gdiv = document.createElement('div');
    gdiv.id = "globalDiv";
    gdiv.style.float = 'left';
    //progressBar
    var div = document.createElement('div');
    div.classList.add('progress');
    var pb_length = 187;
    div.style.width = pb_length+'px'; //HARDCODED...
    div.style.marginBottom = '0px';
    var div1 = document.createElement('div')
    div1.classList.add('progress-bar')
    div1.style.width = 100*(Cpnt)/Tpnt+'%';
    div1.innerHTML = "<strong>"+Cpnt+"</strong>";
    div.appendChild(div1);
    var div1 = document.createElement('div')
    div1.classList.add('progress-bar', 'progress-bar-warning')
    div1.style.width = 100*(Rpnt)/Tpnt+'%'
    div1.innerHTML = "<strong>"+Rpnt+"</strong>";
    div.appendChild(div1);
    gdiv.appendChild(div);
    // table
    var table = document.createElement('table');
    table.classList.add('table', 'table-striped');
    table.style.marginBottom = '5px';
    //head
    var thead = document.createElement('thead');
    var tr = document.createElement('tr');
    var th = document.createElement('th');
    th.innerHTML = "Rank";
    tr.appendChild(th);
    var th = document.createElement('th');
    th.innerHTML = "Requirement (CP)";
    tr.appendChild(th);
    thead.appendChild(tr);
    //body
    var tbody = document.createElement('tbody');
    for (var i=1; i<=maxRank; i++) {
        var tr = document.createElement('tr');
        var td1 = document.createElement('td');
        td1.innerHTML = getRankIcon(i, 20);
        td1.style.padding = "2px";
        var td2 = document.createElement('td');
        td2.innerHTML = Math.floor(Math.pow(rankMultiplier, i));
        td2.style.padding = "2px";
        tr.style.textAlign = "center";
        if (i == rank) { // current org rank
            tr.style.backgroundColor = "#337ab7";
            tr.style.color = "white";
        } else if (i == rank+1) {
            tr.style.backgroundColor = "#f0ad4e";
            tr.style.color = "white";
        }
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
    }
    table.appendChild(thead);
    table.appendChild(tbody);
    gdiv.appendChild(table);
    OuterDiv.appendChild(gdiv);
    // Tot nbr points
    var tableHeight = 440; //HARDCODED...
    var div = document.createElement('div');
    div.classList.add('progress');
    div.style.width = '20px';
    div.style.height = tableHeight+'px'; //HARDCODED...
    div.style.display = 'flex'
    div.style.float = 'left';
    div.style.marginTop = '56px';
    div.style.marginBottom = '0px';
    div.style.marginLeft = '2px';
    var div1 = document.createElement('div')
    div1.classList.add('progress-bar', 'progress-bar-success', 'progress-bar-striped')
    div1.style.height = ((rank+rankDec)*100/16)+'%';
    div1.style.width = '100%';
    div.appendChild(div1);
    OuterDiv.appendChild(div);

    return OuterDiv.outerHTML;
}

function addToTableFromJson(datatable, url) {
    $.getJSON( url, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                row.pnts,
                getRankIcon(row.rank),
                row.logo_path,
                row.org
            ];
            datatable.row.add(to_add);
        }
        datatable.draw();
    });
}

function updateProgressHeader(org) {
    // get Org rank
    $.getJSON( url_getOrgRank+'?org='+org, function( data ) {
        datatableTop.draw();
        var rank = Math.floor(data.rank);
        var rankDec = data.rank-rank;
        $('#btnCurrRank').show();
        $('#orgText').text(data.org);
        var popoverRank = $('#btnCurrRank').data('bs.popover');
        popoverRank.options.content = generateRankingSheet(rank, rankDec, data.stepPts, data.points, data.remainingPts);
        $('#orgRankDiv').html(getRankIcon(rank, 40, true));
        $('#orgNextRankDiv').html(getRankIcon(rank+1, 40, true));
        if (data.rank > 16){
            $('#progressBarDiv').width(1*150); //150 is empty bar width
        } else {
            $('#progressBarDiv').width((data.rank - rank)*150); //150 is empty bar width
        }
        // update color in other dataTables
        datatableTop.rows().every( function() {
            var row = this.node();
            if(this.data()[3] == data.org) { row.classList.add('info'); } else { row.classList.remove('info'); }
        });
        datatableFame.rows().every( function() {
            var row = this.node();
            if(this.data()[3] == data.org) { row.classList.add('info'); } else { row.classList.remove('info'); }
        });
        datatableCateg.rows().every( function() {
            var row = this.node();
            if(this.data()[3] == data.org) { row.classList.add('info'); } else { row.classList.remove('info'); }
        });
        datatableLast.rows().every( function() {
            var row = this.node();
            if(this.data()[3] == data.org) { row.classList.add('info'); } else { row.classList.remove('info'); }
        });
    });
}

function showOnlyOrg() {
    datatableCateg.search( $('#orgText').text() ).draw();
}

$(document).ready(function() {
    if(currOrg != "") // currOrg selected
        updateProgressHeader(org)
    $('#orgName').typeahead(typeaheadOption);
    $('#btnCurrRank').popover(popOverOption);
    datatableTop = $('#topContribTable').DataTable(optionDatatable_top);
    datatableFame = $('#fameTable').DataTable(optionDatatable_fame);
    datatableCateg = $('#categTable').DataTable(optionDatatable_Categ);
    datatableLast = $('#lastTable').DataTable(optionDatatable_last);
    // top contributors
    addToTableFromJson(datatableTop, url_getTopContributor);
    // hall of fame
    addToTableFromJson(datatableFame, url_getFameContributor);
    // last contributors
    addToTableFromJson(datatableLast, url_getLastContributor);
    // category per contributors
    $.getJSON( url_getCategPerContrib, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                i+1,
                getRankIcon(row.rank),
                row.logo_path,
                row.org,
            ];
            for (categ of categ_list) {
                to_add.push(row[categ]);
            }

            datatableCateg.row.add(to_add);
        }
        datatableCateg.draw();
    });
    // top 5 contrib overtime
    $.getJSON( url_getTop5Overtime, function( data ) {
        console.log(data);
        var plotLineChart = $.plot("#divTop5Overtime", data, optionsLineChart);
    });
});
