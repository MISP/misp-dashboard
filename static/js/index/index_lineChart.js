var updateIntervalDirect = 1000*2; // 2s
var updateInterval = 1000*60*60*graph_log_refresh_rate; // 1h
var maxNumPoint = hours_spanned+1;

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
    //colors: ["#2fa1db"],
    yaxis: { min: 0, max: 20 },
    xaxis: { min: 0, max: maxNumPoint },
    ticks: maxNumPoint+1,
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

var rData = [
    { label: "Series1",  data: 10},
    { label: "Series2",  data: 30},
    { label: "Series3",  data: 60}
];
var plotLineChart = $.plot("#feedDiv3", sources.getEmptyData(), optionsLineChart);

function updateChart() {
    sources.slideSource();
    sources.resetCountOnSource();
    plotLineChart.setData(sources.toArray());
    plotLineChart.getOptions().yaxes[0].max = sources.getGlobalMax();
    plotLineChart.setupGrid();
    plotLineChart.draw();
    setTimeout(updateChart, updateInterval);
}
updateChart()

function updateChartDirect() {
    plotLineChart.setData(sources.toArrayDirect());
    plotLineChart.getOptions().yaxes[0].max = sources.getGlobalMax();
    plotLineChart.setupGrid();
    plotLineChart.draw();
    //setTimeout(updateChartDirect, updateIntervalDirect);
}
updateChartDirect()

