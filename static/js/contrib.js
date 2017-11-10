/* GLOB VAR */
var allOrg = [];
var datatableTop;
var datatableFame;
var refresh_speed = min_between_reload*60;
var will_reload = $("#reloadCheckbox").is(':checked');
var sec_before_reload = refresh_speed;
var dataTop5Overtime;
var plotLineChart

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
    colors: ["#2F4F4F", "#778899", "#696969", "#A9A9A9", "#D3D3D3", "#337ab7"],
    points: { show: true },
    lines: { show: true, fill: true },
    grid: {
        tickColor: "#dddddd",
        borderWidth: 0
    },
    legend: {
        show: true,
        position: "nw"
    },
    xaxis: {
        mode: "time",
        timeformat: "%m/%d",
        minTickSize: [1, "day"]
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
    "columnDefs": [
        { className: "centerCellPicOrgRank", "targets": [ 2 ] },
        { className: "centerCellPicOrgLogo", "targets": [ 3 ] },
        { className: "centerCellPicOrgLogo", "targets": [ 4 ] }
    ]
};
var optionDatatable_top = jQuery.extend({}, optionDatatable_light)
var optionDatatable_last = jQuery.extend({}, optionDatatable_light)
optionDatatable_last.columnDefs = [
    { className: "centerCellPicOrgRank", "targets": [ 2 ] },
    { className: "centerCellPicOrgLogo", "targets": [ 3 ] },
    { className: "centerCellPicOrgLogo", "targets": [ 4 ] },
    { 'orderData':[6], 'targets': [0] },
    {
        'targets': [6],
        'visible': false,
        'searchable': false
    },
]
var optionDatatable_fame = jQuery.extend({}, optionDatatable_light)
optionDatatable_fame.scrollY = '45vh';

var optionDatatable_Categ = {
    responsive: true,
    searching: true,
    "order": [[ 0, "desc" ]],
    scrollY:        '38vh',
    "scrollX": true,
    scrollCollapse: true,
    paging:         false,
    "info": false,
    "columnDefs": [
        { className: "centerCellPicOrgRank", "targets": [ 2 ] },
        { className: "centerCellPicOrgLogo", "targets": [ 3 ], 'searchable': false, 'sortable': false },
        { className: "centerCellPicOrgLogo", "targets": [ 4 ]}
    ]
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
function getMonthlyRankIcon(rank, size, header) {
    if (rank > 16) {
        var rankLogoPath = url_baseRankMonthlyLogo+0+'.svg';
    } else {
        var rankLogoPath = url_baseRankMonthlyLogo+rank+'.svg';
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

function getOrgRankIcon(rank, size) {
    if (rank > 16) {
        var rankLogoPath = url_baseOrgRankLogo+0+'.svg';
    } else {
        var rankLogoPath = url_baseOrgRankLogo+rank+'.svg';
    }
    var obj = document.createElement('img');
    obj.height = size/2;
    obj.width = size;
    obj.src = rankLogoPath;
    obj.type = "image/svg"
    obj.title = org_rank_obj[rank];
    obj.classList.add('orgRankClass')
    return obj.outerHTML;
}

function createImg(source, size) {
    var obj = document.createElement('img');
    obj.height = size;
    obj.width = size;
    obj.style.margin = 'auto';
    obj.src = source;
    obj.type = "image/png"
    obj.alt = ""
    return obj.outerHTML;
}

function createHonorImg(array, size) {
    size = 32;
    var div = document.createElement('div');
    for (badgeNum of array) {
        var obj = document.createElement('img');
        obj.height = size;
        obj.width = size;
        obj.style.margin = 'auto';
        obj.title = org_honor_badge_title[badgeNum];
        obj.src = url_baseHonorLogo+badgeNum+'.svg';
        div.appendChild(obj);
    }
    return div.outerHTML;
}

function createOrgLink(org) {
    var a = document.createElement('a');
    a.innerHTML = org;
    a.href = "?org="+org;
    return a.outerHTML;
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
        td1.innerHTML = getMonthlyRankIcon(i, 40);
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
    var tableHeight = 720; //HARDCODED...
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
                getMonthlyRankIcon(row.rank),
                getOrgRankIcon(row.orgRank, 60),
                createHonorImg(row.honorBadge, 20),
                createImg(row.logo_path, 32),
                createOrgLink(row.org)
            ];
            datatable.row.add(to_add);
        }
        datatable.draw();
    });
}

function addLastFromJson(datatable, url) {
    $.getJSON( url, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            addLastContributor(datatable, row);
        }
        datatable.draw();
    });
}

function addLastContributor(datatable, data, update) {
    var to_add = [
        data.pnts,
        getMonthlyRankIcon(data.rank),
        getOrgRankIcon(data.orgRank, 60),
        createHonorImg(data.honorBadge, 20),
        createImg(data.logo_path, 32),
        createOrgLink(data.org),
        data.epoch
    ];
    if (update == undefined || update == false) {
        datatable.row.add(to_add);
    } else if(update == true) {
        datatable.rows().every( function() {
            if(this.data()[3] == data.org) {
                datatable.row( this ).data( to_add );
            }
        });
    }
}

function updateProgressBar(org) {
    if(currOrg != org)
        return;
    $.getJSON( url_getOrgRank+'?org='+org, function( data ) {
        var rank = Math.floor(data.rank);
        var rankDec = data.rank-rank;
        var popoverRank = $('#btnCurrRank').data('bs.popover');
        popoverRank.options.content = generateRankingSheet(rank, rankDec, data.stepPts, data.points, data.remainingPts);
        $('#orgRankDiv').html(getMonthlyRankIcon(rank, 40, true));
        $('#orgNextRankDiv').html(getMonthlyRankIcon(rank+1, 40, true));
        if (data.rank > 16){
            $('#progressBarDiv').width(1*150); //150 is empty bar width
        } else {
            $('#progressBarDiv').width((data.rank - rank)*150); //150 is empty bar width
        }
    });
}

function updateOvertakePnts() {
    var prevOrgName = "";
    var prevOrgPnts = 0;
    datatableTop.rows().every( function() {
        var row = this.node();
        var orgRowName = $(this.data()[5])[0].text; // contained in <a>
        var orgRowPnts = this.data()[0]
        if(orgRowName == currOrg) {
            if(prevOrgName == ""){ //already first
                $('#orgToOverTake').text(orgRowName);
                $('#pntsToOvertakeNext').text(0);
            } else {
                $('#orgToOverTake').text(prevOrgName);
                $('#pntsToOvertakeNext').text(parseInt(prevOrgPnts)-orgRowPnts);
            }
        } else {
            prevOrgName = orgRowName;
            prevOrgPnts = orgRowPnts;
        }
    });
}

function updateProgressHeader(org) {
    currOrg = org;
    // get Org rank
    $.getJSON( url_getOrgRank+'?org='+org, function( data ) {
        datatableTop.draw();
        var rank = Math.floor(data.rank);
        var rankDec = data.rank-rank;
        $('#btnCurrRank').show();
        $('#orgText').text(data.org);
        var popoverRank = $('#btnCurrRank').data('bs.popover');
        popoverRank.options.content = generateRankingSheet(rank, rankDec, data.stepPts, data.points, data.remainingPts);
        $('#orgRankDiv').html(getMonthlyRankIcon(rank, 40, true));
        $('#orgNextRankDiv').html(getMonthlyRankIcon(rank+1, 40, true));
        if (data.rank > 16){
            $('#progressBarDiv').width(1*150); //150 is empty bar width
        } else {
            $('#progressBarDiv').width((data.rank - rank)*150); //150 is empty bar width
        }
        // update color in other dataTables
        datatableTop.rows().every( function() {
            var row = this.node();
            if(this.data()[5] == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
        });
        datatableFame.rows().every( function() {
            var row = this.node();
            if(this.data()[5] == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
        });
        datatableCateg.rows().every( function() {
            var row = this.node();
            if(this.data()[5] == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
        });
        datatableLast.rows().every( function() {
            var row = this.node();
            if(this.data()[5] == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
        });
    });

    // colorize row contribution rank help
    $.getJSON( url_getContributionOrgStatus+'?org='+org, function( data ) {
        var status = data['status'];
        var curContributionOrgRank = data['rank'];
        var totNumPoints = data['totPoints']
        $('#orgTotNumOfPoint').text(totNumPoints);
        if (curContributionOrgRank == 0) {
            $('#orgContributionRank').attr('data', '');
        } else {
            $('#orgContributionRank').attr('data', url_baseOrgRankLogo+curContributionOrgRank+'.svg');
        }
        for (var row of $('#bodyTablerankingModal')[0].children) {
            row = $(row);
            var firstCell = $(row.children()[0]);
            var rank = row.data('rank');
            //remove all classes
            row.removeClass("warning");
            row.removeClass("danger");
            row.removeClass("success");
            firstCell.removeClass("successCell");
            //add correct class
            if(status[rank] == 0){
                row.addClass("danger");
            } else if(status[rank] == 1) {
                row.addClass("warning");
            }
            if(rank == curContributionOrgRank) {
                firstCell.addClass("successCell");
            }
        }
    });

    // colorize badge if acquired
    $.getJSON( url_getHonorBadges+'?org='+org, function( data ) {
        for(var i=0; i<numberOfBadges; i++) { // remove
            $('#divBadge_'+(i+1)).removeClass('circlBadgeAcquired');
        }
        for(var i=0; i<data.length; i++) { // add
            $('#divBadge_'+(data[i])).addClass('circlBadgeAcquired');
        }
    });

    //update overtake points
    updateOvertakePnts();

    //Add new data to linechart
    var flag_already_displayed = false;
    for(obj of dataTop5Overtime) { //check if already displayed
        if (obj.label == currOrg) {
            flag_already_displayed = true;
            break;
        }
    }
    if (!flag_already_displayed) {
        $.getJSON( url_getOrgOvertime+'?org='+org, function( data ) {
            var toPlot = dataTop5Overtime.slice(0); //cloning data
            // transform secs into date
            var new_data = [];
            for(list of data['data']) {
                new_data.push([new Date(list[0]*1000), list[1]]);
            }
            data['data'] = new_data;
            toPlot.push(data);

            plotLineChart.setData(toPlot);
            plotLineChart.setupGrid();
            plotLineChart.draw();
        });
    }
}

function showOnlyOrg() {
    datatableCateg.search( $('#orgText').text() ).draw();
}

function timeToString(time) {
    var min = Math.floor(time / 60);
    min = (min < 10) ? ("0" + min) : min;
    var sec = time - 60*min;
    sec = (sec < 10) ? ("0" + sec) : sec;
    return min + ":" + sec
}

function updateTimer() {
    if ($("#reloadCheckbox").is(':checked')) {
        sec_before_reload--;
        if (sec_before_reload < 1) {
            source_lastContrib.close();
            location.reload();
        } else {
            $('#labelRemainingTime').text(timeToString(sec_before_reload));
            setTimeout(function(){ updateTimer(); }, 1000);
        }
    } else {
        sec_before_reload = refresh_speed;
    }
}

$(':checkbox').change(function() {
    if ($("#reloadCheckbox").is(':checked')) { setTimeout(function(){ updateTimer(); }, 1000); }
});

$(document).ready(function() {
    $('#labelRemainingTime').text(timeToString(sec_before_reload));
    updateTimer();
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
    addLastFromJson(datatableLast, url_getLastContributor);
    // category per contributors
    $.getJSON( url_getCategPerContrib, function( data ) {
        for (i in data) {
            var row = data[i];
            i = parseInt(i);
            var to_add = [
                row.pnts,
                getMonthlyRankIcon(row.rank),
                getOrgRankIcon(row.orgRank, 44),
                createHonorImg(row.honorBadge, 20),
                createImg(row.logo_path, 32),
                createOrgLink(row.org),
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
        // transform secs into date
        for(i in data){
            var new_data = [];
            for(list of data[i]['data']) {
                new_data.push([new Date(list[0]*1000), list[1]]);
            }
            data[i]['data'] = new_data;
        }
        dataTop5Overtime = data;
        plotLineChart = $.plot("#divTop5Overtime", data, optionsLineChart);
    });
    if(currOrg != "") // currOrg selected
        //FIXME: timeout used to wait that all datatables are draw.
        setTimeout( function() { updateProgressHeader(currOrg); }, 400);

    source_lastContrib = new EventSource(url_eventStreamLastContributor);
    source_lastContrib.onmessage = function(event) {
        var json = jQuery.parseJSON( event.data );
        addLastContributor(datatableLast, json, true);
        datatableLast.draw();
        updateProgressBar(json.org);
        updateOvertakePnts();
        sec_before_reload = refresh_speed; //reset timer at each contribution
    };
});
