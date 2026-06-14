// charts.js — Premium Chart.js helper integrations

// Get theme-specific chart config values
function getChartColors() {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    return {
        text: isLight ? '#475569' : '#94a3b8',
        grid: isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.05)',
        tooltipBg: isLight ? '#ffffff' : '#0f1535',
        tooltipText: isLight ? '#1e293b' : '#e2e8f0',
        tooltipBorder: isLight ? 'rgba(0, 0, 0, 0.1)' : 'rgba(102, 126, 234, 0.2)',
        fonts: {
            family: "'Inter', sans-serif"
        }
    };
}

// Global charts registry so we can destroy/recreate them
const ChartRegistry = {};

function registerChart(name, chartInstance) {
    if (ChartRegistry[name]) {
        ChartRegistry[name].destroy();
    }
    ChartRegistry[name] = chartInstance;
}

// 1. Doughnut Chart: File Temperature Distribution
function createTemperatureChart(canvasId, hot, warm, cold, archive) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    const colors = getChartColors();
    
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Hot Files', 'Warm Files', 'Cold Files', 'Archive Files'],
            datasets: [{
                data: [hot, warm, cold, archive],
                backgroundColor: [
                    '#ef4444', // Hot
                    '#f59e0b', // Warm
                    '#3b82f6', // Cold
                    '#6b7280'  // Archive
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: colors.text,
                        font: colors.fonts,
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 10
                }
            },
            cutout: '75%'
        }
    });
    
    registerChart(canvasId, chart);
}

// 2. Bar Chart: Access Frequency (Top Files)
function createAccessChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    const colors = getChartColors();
    
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Access Count',
                data: data,
                backgroundColor: 'rgba(102, 126, 234, 0.7)',
                borderColor: '#667eea',
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: colors.fonts }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: colors.text, font: colors.fonts }
                }
            }
        }
    });
    
    registerChart(canvasId, chart);
}

// 3. Pie Chart: File Types Distribution
function createFileTypeChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    const colors = getChartColors();
    
    const chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#667eea', // Text/Code
                    '#764ba2', // Images
                    '#00d4ff', // Documents
                    '#10b981', // Archives
                    '#f59e0b', // Binaries
                    '#8b5cf6', // Audio/Video
                    '#94a3b8'  // Other
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: colors.text,
                        font: colors.fonts,
                        padding: 12
                    }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 8
                }
            }
        }
    });
    
    registerChart(canvasId, chart);
}

// 4. Line Chart: Storage Savings over Time
function createStorageTimeline(canvasId, labels, originalData, compressedData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    const colors = getChartColors();
    
    // Create gradient
    const gradientOriginal = ctx.getContext('2d').createLinearGradient(0, 0, 0, 400);
    gradientOriginal.addColorStop(0, 'rgba(102, 126, 234, 0.2)');
    gradientOriginal.addColorStop(1, 'rgba(102, 126, 234, 0)');
    
    const gradientCompressed = ctx.getContext('2d').createLinearGradient(0, 0, 0, 400);
    gradientCompressed.addColorStop(0, 'rgba(0, 212, 255, 0.2)');
    gradientCompressed.addColorStop(1, 'rgba(0, 212, 255, 0)');
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Original Size (MB)',
                    data: originalData,
                    borderColor: '#667eea',
                    backgroundColor: gradientOriginal,
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                },
                {
                    label: 'Optimized Size (MB)',
                    data: compressedData,
                    borderColor: '#00d4ff',
                    backgroundColor: gradientCompressed,
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: colors.text, font: colors.fonts }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: colors.fonts }
                },
                y: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: colors.fonts }
                }
            }
        }
    });
    
    registerChart(canvasId, chart);
}

// 5. Grouped Bar: Compression Efficiency by Algorithm
function createEfficiencyChart(canvasId, labels, ratios) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    const colors = getChartColors();
    
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Compression Ratio (lower is better)',
                data: ratios,
                backgroundColor: 'rgba(118, 75, 162, 0.7)',
                borderColor: '#764ba2',
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: colors.fonts }
                },
                y: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: colors.fonts },
                    suggestedMax: 1
                }
            }
        }
    });
    
    registerChart(canvasId, chart);
}

// Listen to theme change events to update colors
document.addEventListener('themeChanged', () => {
    const chartsToRebuild = Object.keys(ChartRegistry);
    // Trigger window resize or custom redraw for dynamic changes
    // In practice, chart.js needs a configuration update
    chartsToRebuild.forEach(name => {
        const chartInstance = ChartRegistry[name];
        if (chartInstance) {
            const colors = getChartColors();
            
            // Update scales
            if (chartInstance.options.scales) {
                if (chartInstance.options.scales.x) {
                    chartInstance.options.scales.x.grid.color = colors.grid;
                    chartInstance.options.scales.x.ticks.color = colors.text;
                }
                if (chartInstance.options.scales.y) {
                    chartInstance.options.scales.y.grid.color = colors.grid;
                    chartInstance.options.scales.y.ticks.color = colors.text;
                }
            }
            
            // Update legend/tooltips
            if (chartInstance.options.plugins) {
                if (chartInstance.options.plugins.legend && chartInstance.options.plugins.legend.labels) {
                    chartInstance.options.plugins.legend.labels.color = colors.text;
                }
                if (chartInstance.options.plugins.tooltip) {
                    chartInstance.options.plugins.tooltip.backgroundColor = colors.tooltipBg;
                    chartInstance.options.plugins.tooltip.titleColor = colors.tooltipText;
                    chartInstance.options.plugins.tooltip.bodyColor = colors.tooltipText;
                    chartInstance.options.plugins.tooltip.borderColor = colors.tooltipBorder;
                }
            }
            chartInstance.update();
        }
    });
});
