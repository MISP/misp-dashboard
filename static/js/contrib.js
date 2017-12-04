/* GLOB VAR */
var allOrg = [];
var datatableTop;
var datatableFameQuant;
var refresh_speed = min_between_reload*60;
var next_effect = new Date();
var will_reload = $("#reloadCheckbox").is(':checked');
var sec_before_reload = refresh_speed;
var plotLineChart;
var source_awards;
var source_lastContrib;

/* CONFIG */
var maxRank = 16;
var popOverOption = {
    trigger: "hover",
    html: true,
    placement: 'bottom',
    content: generateRankingSheet(),
    template: '<div class="popover" role="tooltip"><div class="arrow"></div><h3 class="popover-title"></h3><div class="popover-content popoverNoPadding"></div></div>'
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
optionDatatable_last["ordering"] = true;
optionDatatable_last["order"] = [[ 0, "dec" ]];
optionDatatable_last.columnDefs = [
    { className: "small", "targets": [ 0 ] },
    { className: "verticalAlign", "targets": [ 1 ] },
    { className: "centerCellPicOrgRank verticalAlign", "targets": [ 2 ] },
    { className: "centerCellPicOrgLogo", "targets": [ 3 ] },
    { className: "centerCellPicOrgLogo verticalAlign", "targets": [ 4 ] },
    { className: "centerCellPicOrgLogo verticalAlign", "targets": [ 5 ] },
    { className: "verticalAlign", "targets": [ 6 ] }
]
var optionDatatable_fameQuant = jQuery.extend({}, optionDatatable_light)
var optionDatatable_fameQual = jQuery.extend({}, optionDatatable_light)
optionDatatable_fameQual.scrollY = '39vh';

var optionDatatable_Categ = {
    responsive: true,
    searching: true,
    "order": [[ 0, "desc" ]],
    scrollY:        '35vh',
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
var optionDatatable_awards = jQuery.extend({}, optionDatatable_light);
optionDatatable_awards["ordering"] = true;
optionDatatable_awards["order"] = [[ 0, "dec" ]];
optionDatatable_awards["scrollX"] = false;
optionDatatable_awards["scrollY"] = "40vh";
optionDatatable_awards.columnDefs = [
    { className: "centerCellPicOrgLogo verticalAlign", "targets": [ 1 ] },
    { className: "centerCellPicOrgLogo", "targets": [ 3 ] },
];

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

function createTrophyImg(rank, size, categ) {
    var obj = document.createElement('img');
    obj.height = size;
    obj.width = size;
    obj.style.margin = 'auto';
    obj.src = url_baseTrophyLogo+rank+'.png';;
    obj.title = trophy_title[rank] + " in " + categ;
    obj.type = "image/png"
    obj.alt = ""
    return obj.outerHTML;
}

function createHonorImg(array, size) {
    size = 32;
    var div = document.createElement('div');
    div.style.boxShadow = '0px 0px 5px #00000099';
    div.style.backgroundColor = '#e1e1e1';
    if (!Array.isArray(array))
        array = [array];
    for (badgeNum of array) {
        var obj = document.createElement('img');
        obj.height = size;
        obj.width = size;
        obj.style.margin = 'auto';
        obj.title = org_honor_badge_title[badgeNum];
        obj.src = url_baseHonorLogo+badgeNum+'.svg';
        div.appendChild(obj);
    }
    div.style.width = 32*array.length+'px';
    div.style.borderRadius = '15px';
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
    var date = new Date(data.epoch*1000);
    date.toString = function() {return this.toTimeString().slice(0,-15) +' '+ this.toLocaleDateString(); };
    var to_add = [
        date,
        data.pnts,
        getMonthlyRankIcon(data.rank),
        getOrgRankIcon(data.orgRank, 60),
        createHonorImg(data.honorBadge, 20),
        createImg(data.logo_path, 32),
        createOrgLink(data.org),
    ];
    if (update == undefined || update == false) {
        datatable.row.add(to_add);
        datatable.draw();
    } else if(update == true) {
        var row_added = false;
        datatable.rows().every( function() {
            if($(this.data()[6])[0].text == data.org) {
                var node = $(datatable.row( this ).node());
                datatable.row( this ).data( to_add );
                if(next_effect <= new Date()) {
                    node.effect("slide", 500);
                    next_effect.setSeconds((new Date()).getSeconds() + 5);
                }
                row_added = true;
            }
            datatable.draw();
        });
        if (!row_added) {
            var node = $(datatable.row.add(to_add).draw().node());
            node.effect("slide", 700);
        }
    }
}

function addAwards(datatableAwards, json, playAnim) {
    if(json.award[0] == 'contribution_status') {
        var award = getOrgRankIcon(json.award[1], 60);
    } else if (json.award[0] == 'badge') {
        var award = createHonorImg(json.award[1], 20);
    } else if (json.award[0] == 'trophy') {
        var categ = json.award[1][0];
        var award = createTrophyImg(json.award[1][1], 40, categ);
    }
    var date = new Date(json.epoch*1000);
    date.toString = function() {return this.toTimeString().slice(0,-15) +' '+ this.toLocaleDateString(); };
    var to_add = [
        date,
        createImg(json.logo_path, 32),
        createOrgLink(json.org),
        award,
    ];
    var node = $(datatableAwards.row.add(to_add).draw().node());
    if(playAnim)
        node.effect("slide", 700);
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
            var orgRowName = $(this.data()[5])[0].text;
            if(orgRowName == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
        });
        datatableFameQuant.rows().every( function() {
            var row = this.node();
            var orgRowName = $(this.data()[5])[0].text;
            if(orgRowName == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
        });
        datatableCateg.rows().every( function() {
            var row = this.node();
            var orgRowName = $(this.data()[5])[0].text;
            if(orgRowName == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
        });
        datatableLast.rows().every( function() {
            var row = this.node();
            var orgRowName = $(this.data()[6])[0].text;
            if(orgRowName == data.org) { row.classList.add('selectedOrgInTable'); } else { row.classList.remove('selectedOrgInTable'); }
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
            $('#divBadge_'+(i+1)).addClass('circlBadgeNotAcquired');
        }
        for(var i=0; i<data.length; i++) { // add
            $('#divBadge_'+(i+1)).removeClass('circlBadgeNotAcquired');
            $('#divBadge_'+(data[i])).addClass('circlBadgeAcquired');
        }
    });

    // set trophies if acquired
    $.getJSON( url_getTrophies+'?org='+org, function( data ) {
        var source = url_baseTrophyLogo+0+'.png'
        for(var i=0; i<trophy_categ_list.length; i++) { // remove
            categ = trophy_categ_list[i];
            $('#trophy_'+categ).attr('src', source);
            $('#trophy_'+categ).attr('title', "");
            try { // in case popover not created
                var pop = $('#trophy_'+categ).data('bs.popover');
                pop.destroy();
            } catch(err) {

            }
        }
        setTimeout(function() { // avoid race condition with destroy
            for(var i=0; i<data.length; i++) { // add
                categ = data[i].categ;
                rank = data[i].trophy_true_rank;
                trophy_points = data[i].trophy_points
                source = url_baseTrophyLogo+rank+'.png'
                $('#trophy_'+categ).attr('src', source);
                $('#trophy_'+categ).attr('title', trophy_title[rank]);
                $('#trophy_'+categ).popover({title: trophy_title[rank], content: 'Level: '+rank+' ('+trophy_points+' points)', trigger: "hover", placement: "bottom"});
            }
        }, 300);
    });

    //update overtake points
    updateOvertakePnts();
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

    $(window).on("beforeunload", function() {
        source_lastContrib.close();
        source_awards.close();
    });

    datatableTop = $('#topContribTable').DataTable(optionDatatable_top);
    datatableFameQuant = $('#fameTableQuantity').DataTable(optionDatatable_fameQuant);
    datatableFameQual = $('#fameTableQuality').DataTable(optionDatatable_fameQual);
    datatableCateg = $('#categTable').DataTable(optionDatatable_Categ);
    datatableLast = $('#lastTable').DataTable(optionDatatable_last);
    datatableAwards = $('#awardTable').DataTable(optionDatatable_awards);
    // top contributors
    addToTableFromJson(datatableTop, url_getTopContributor);
    // hall of fame
    addToTableFromJson(datatableFameQuant, url_getFameContributor);
    addToTableFromJson(datatableFameQual, url_getFameQualContributor);
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
    // latest awards
    $.getJSON( url_getLatestAwards, function( data ) {
        for (i in data) {
            addAwards(datatableAwards, data[i], false);
        }
    });

    if(currOrg != "") // currOrg selected
        //FIXME: timeout used to wait that all datatables are draw.
        setTimeout( function() { updateProgressHeader(currOrg); }, 700);

    source_lastContrib = new EventSource(url_eventStreamLastContributor);
    source_lastContrib.onmessage = function(event) {
        var json = jQuery.parseJSON( event.data );
        addLastContributor(datatableLast, json, true);
        updateProgressBar(json.org);
        updateOvertakePnts();
        sec_before_reload = refresh_speed; //reset timer at each contribution
    };

    source_awards = new EventSource(url_eventStreamAwards);
    source_awards.onmessage = function(event) {
        var json = jQuery.parseJSON( event.data );
        addAwards(datatableAwards, json, true);
        updateProgressHeader(currOrg);
    };
});
