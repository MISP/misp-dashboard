function labelFormatter(label, series) {
    return "<div style='font-size:8pt; text-align:center; padding:2px; color:white;'>"
+ label + "<br/>" + Math.round(series.percent) + "%</div>";
}
var optionsPieChart = {
    series: {
        pie: {
            innerRadius: 0.5,
            show: true,
            label: {
                show: true,
                radius: 1,
                formatter: labelFormatter,
                background: {
                    opacity: 0.7,
                    color: '#000'
                }
            }
        }
    },
    legend: {
        show: false
    }
};

var plotPieChartA = $.plot("#feedDiv1A", rData, optionsPieChart);
var plotPieChartB = $.plot("#feedDiv1B", rData, optionsPieChart);
