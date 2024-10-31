const dateRangeSelect = document.getElementById('date-range');
const customDateRangeDiv = document.getElementById('custom-date-range')
const startDateInput = document.getElementById('start-date');
const endDateInput = document.getElementById('end-date');
const chartCanvas = document.getElementById('my-chart');
const chartCanvas2 = document.getElementById('my-chart-2');
const chartCanvas3 = document.getElementById('my-chart-3');

let chartData = [];
let top10Data = [];
let imageTop10Data = [];
let viewChart;
let viewChartTop10;
let viewChartImageTop10;

// Fetch CSV data on page load
window.addEventListener('load', () => {
    fetch('elxr_org_view.csv')
        .then(response => response.text())
        .then(csvData => {
            chartData = parseCSV(csvData);
            dateRangeSelect.selectedIndex = 2;
            dateRangeSelect.dispatchEvent(new Event('change'));
        })
        .catch(error => {
            console.error('Error fetching CSV data:', error);
        });
});

window.addEventListener('load', () => {
    fetch('package_top_10.csv')
        .then(response => response.text())
        .then(csvData => {
            top10Data = parseCSV(csvData);
            drawTop10Chart(top10Data);
        })
        .catch(error => {
            console.error('Error fetching CSV data:', error);
        });
});

window.addEventListener('load', () => {
    fetch('image_top_10.csv')
        .then(response => response.text())
        .then(csvData => {
            imageTop10Data = parseCSV(csvData);
            drawImageTop10Chart(imageTop10Data);
        })
        .catch(error => {
            console.error('Error fetching CSV data:', error);
        });
});

function rangeChange() {
    if (startDateInput.value != '' && endDateInput.value != '') {
        startDate = new Date(startDateInput.value);
        endDate = new Date(endDateInput.value);
        // Filter the data based on the date range
        filteredData = chartData.filter(item => {
            const itemDate = new Date(item.TimeBucket);
            return itemDate >= startDate && itemDate <= endDate;
        });

        drawChart(filteredData);
    }
}

startDateInput.addEventListener('change', rangeChange);
endDateInput.addEventListener('change', rangeChange);

dateRangeSelect.addEventListener('change', () => {
    const selectedRange = dateRangeSelect.value;
    const today = new Date();

    if (selectedRange === 'custom') {
        customDateRangeDiv.style.display = 'block';
    } else {
        customDateRangeDiv.style.display = 'none';
    }
    switch (selectedRange) {
        case '24h':
            const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
            startDateInput.value = yesterday.toISOString().slice(0, 10);
            endDateInput.value = today.toISOString().slice(0, 10);
            break;
        case '1w':
            const aWeekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
            startDateInput.value = aWeekAgo.toISOString().slice(0, 10);
            endDateInput.value = today.toISOString().slice(0, 10);
            break;
        case '1m':
            const aMonthAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
            startDateInput.value = aMonthAgo.toISOString().slice(0, 10);
            endDateInput.value = today.toISOString().slice(0, 10);
            break;
        case 'custom':
            // Clear the input fields
            //startDateInput.value = '';
            //endDateInput.value = '';
            //customDateRangeDiv.style.display = 'block';
            break;
    }
    rangeChange();
});

function drawChart(data) {
    const ctx = chartCanvas.getContext('2d');
    if (viewChart) {
        viewChart.destroy();  // Destroy existing chart to prevent duplication
    }
    viewChart = new Chart(ctx, {
        type: 'line', // Adjust the chart type as needed
        data: {
            labels: data.map(item => item.TimeBucket),
            datasets: [
                {
                    label: 'View Count',
                    data: data.map(item => item.ViewCount),
                    borderColor: 'skyblue',
                    fill: false,
                    yAxisID: 'y',
                    cubicInterpolationMode: 'monotone',
                    tension: 0.4
                },
                {
                    label: 'Unique User',
                    data: data.map(item => item.UniqueUser),
                    borderColor: 'coral',
                    fill: false,
                    yAxisID: 'y1',
                    cubicInterpolationMode: 'monotone',
                    tension: 0.4
                },
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time (UTC)'
                    }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    display: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'View Count'
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    display: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Unique User'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                },
            },
            plugins: {
                title: {
                    display: true,
                    text: 'eLxr Site View Count'
                },
                legend: {
                    display: true,
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function drawTop10Chart(data) {
    const ctx = chartCanvas2.getContext('2d');
    if (viewChartTop10) {
        viewChartTop10.destroy();  // Destroy existing chart to prevent duplication
    }
    viewChartTop10 = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.Name),
            datasets: [{
                data: data.map(item => item.Download),
                backgroundColor: [
                    'skyblue',
                    'coral',
                    'mediumseagreen',
                    'salmon',
                    'teal',
                    'lightcoral',
                    'khaki',
                    'plum',
                    'steelblue',
                    'gold'
                ],
                borderColor: [
                    'deepskyblue',
                    'tomato',
                    'seagreen',
                    'darksalmon',
                    'darkcyan',
                    'indianred',
                    'darkkhaki',
                    'mediumorchid',
                    'darkslateblue',
                    'goldenrod'
                ],
                borderWidth: 1,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Top 10 Most Download Packages'
                },
                legend: {
                    display: false,
                    position: 'right',
                }
            },
        }
    });
}

function drawImageTop10Chart(data) {
    const ctx = chartCanvas3.getContext('2d');
    if (viewChartImageTop10) {
        viewChartImageTop10.destroy();  // Destroy existing chart to prevent duplication
    }
    viewChartImageTop10 = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.Name),
            datasets: [{
                data: data.map(item => item.Download),
                backgroundColor: [
                    'skyblue',
                    'coral',
                    'mediumseagreen',
                    'salmon',
                    'teal',
                    'lightcoral',
                    'khaki',
                    'plum',
                    'steelblue',
                    'gold'
                ],
                borderColor: [
                    'deepskyblue',
                    'tomato',
                    'seagreen',
                    'darksalmon',
                    'darkcyan',
                    'indianred',
                    'darkkhaki',
                    'mediumorchid',
                    'darkslateblue',
                    'goldenrod'
                ],
                borderWidth: 1,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Top 10 Most Download Images'
                },
                legend: {
                    display: false,
                    position: 'right',
                }
            },
        }
    });
}

function parseCSV(csvData) {
    const normalized = csvData.replace(/\r\n|\r/g, '\n');
    const lines = normalized.split('\n');
    const headers = lines[0].split(',');
    const dataArray = [];
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const item = {};
        for (let j = 0; j < headers.length; j++) {
            item[headers[j]] = values[j];
        }
        dataArray.push(item);
    }
    return dataArray;
}
