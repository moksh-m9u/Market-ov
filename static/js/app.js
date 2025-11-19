let attributionResults = null;
let attributionChart = null;
let comparisonChart = null;
let budgetChart = null;
let channelPerfChart = null;

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;
        
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName + 'View').classList.add('active');
    });
});

// Run Attribution Models
document.getElementById('runAttribution').addEventListener('click', async () => {
    const btn = document.getElementById('runAttribution');
    const btnText = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');
    
    btn.disabled = true;
    btnText.textContent = 'Running Analysis...';
    loader.style.display = 'inline-block';
    
    try {
        const response = await fetch('/run_attribution', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            attributionResults = data.results;
            displayAnalytics(data.analytics);
            displayResults(data.results, data.analytics);
            document.getElementById('analyticsSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('budgetSection').style.display = 'block';
            setupChannelLimits(Object.keys(data.results));
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
            if (data.traceback) {
                console.error(data.traceback);
            }
        }
    } catch (error) {
        alert('Error running attribution models: ' + error);
        console.error(error);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Run Attribution Models';
        loader.style.display = 'none';
    }
});

function displayAnalytics(analytics) {
    const grid = document.getElementById('analyticsGrid');
    grid.innerHTML = `
        <div class="analytics-card">
            <div class="label">Total Interactions</div>
            <div class="value">${analytics.total_interactions.toLocaleString()}</div>
            <div class="subtext">User touchpoints</div>
        </div>
        <div class="analytics-card">
            <div class="label">Total Conversions</div>
            <div class="value">${analytics.total_conversions.toLocaleString()}</div>
            <div class="subtext">Successful outcomes</div>
        </div>
        <div class="analytics-card">
            <div class="label">Conversion Rate</div>
            <div class="value">${analytics.conversion_rate}%</div>
            <div class="subtext">Overall performance</div>
        </div>
        <div class="analytics-card">
            <div class="label">Unique Users</div>
            <div class="value">${analytics.unique_users.toLocaleString()}</div>
            <div class="subtext">Individual customers</div>
        </div>
    `;
}

function displayResults(results, analytics) {
    const tbody = document.getElementById('resultsTableBody');
    tbody.innerHTML = '';
    
    for (const [channel, values] of Object.entries(results)) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${channel}</strong></td>
            <td>${values['LastTouch'].toFixed(2)}%</td>
            <td>${values['FirstTouch'].toFixed(2)}%</td>
            <td>${values['LastNonDirect'].toFixed(2)}%</td>
            <td>${values['Linear'].toFixed(2)}%</td>
            <td>${values['UShaped'].toFixed(2)}%</td>
            <td>${values['PositionDecay'].toFixed(2)}%</td>
            <td>${values['Markov'].toFixed(2)}%</td>
            <td class="highlight"><strong>${values['Mean'].toFixed(2)}%</strong></td>
        `;
        tbody.appendChild(row);
    }
    
    displayChannelStats(results, analytics.channel_stats);
    createAttributionChart(results);
    createComparisonChart(results);
}

function displayChannelStats(results, channelStats) {
    const tbody = document.getElementById('channelStatsBody');
    tbody.innerHTML = '';
    
    for (const [channel, stats] of Object.entries(channelStats)) {
        const attribution = results[channel] ? results[channel]['Mean'] : 0;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${channel}</strong></td>
            <td>${stats.interactions.toLocaleString()}</td>
            <td>${stats.conversions.toLocaleString()}</td>
            <td>${stats.conversion_rate.toFixed(2)}%</td>
            <td>$${stats.avg_conversion_value.toFixed(2)}</td>
            <td><strong>${attribution.toFixed(2)}%</strong></td>
        `;
        tbody.appendChild(row);
    }
    
    createChannelPerformanceChart(channelStats, results);
}

function createAttributionChart(results) {
    const ctx = document.getElementById('attributionChart');
    
    if (attributionChart) {
        attributionChart.destroy();
    }
    
    const channels = Object.keys(results);
    const meanValues = channels.map(ch => results[ch]['Mean']);
    
    attributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: channels,
            datasets: [{
                label: 'Mean Attribution (%)',
                data: meanValues,
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(17, 153, 142, 0.8)',
                    'rgba(56, 239, 125, 0.8)',
                    'rgba(255, 159, 64, 0.8)'
                ],
                borderColor: [
                    'rgba(102, 126, 234, 1)',
                    'rgba(118, 75, 162, 1)',
                    'rgba(17, 153, 142, 1)',
                    'rgba(56, 239, 125, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Mean Attribution by Channel',
                    font: {
                        size: 18
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Attribution (%)'
                    }
                }
            }
        }
    });
}

function createComparisonChart(results) {
    const ctx = document.getElementById('comparisonChart');
    
    if (comparisonChart) {
        comparisonChart.destroy();
    }
    
    const channels = Object.keys(results);
    const models = ['LastTouch', 'FirstTouch', 'LastNonDirect', 'Linear', 
                   'UShaped', 'PositionDecay', 'Markov'];
    const modelLabels = ['Last Touch', 'First Touch', 'Last Non-Direct', 'Linear', 
                        'U-Shaped', 'Position Decay', 'Markov'];
    
    const datasets = models.map((model, idx) => {
        const colors = [
            'rgba(255, 99, 132, 0.7)',
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(102, 126, 234, 0.7)',
            'rgba(118, 75, 162, 0.7)'
        ];
        
        return {
            label: modelLabels[idx],
            data: channels.map(ch => results[ch][model]),
            backgroundColor: colors[idx],
            borderColor: colors[idx].replace('0.7', '1'),
            borderWidth: 1
        };
    });
    
    comparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: channels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Attribution Model Comparison',
                    font: {
                        size: 18
                    }
                },
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Attribution (%)'
                    }
                }
            }
        }
    });
}

function createChannelPerformanceChart(channelStats, results) {
    const ctx = document.getElementById('channelPerformanceChart');
    
    if (channelPerfChart) {
        channelPerfChart.destroy();
    }
    
    const channels = Object.keys(channelStats);
    const conversionRates = channels.map(ch => channelStats[ch].conversion_rate);
    const attributionScores = channels.map(ch => results[ch] ? results[ch]['Mean'] : 0);
    
    channelPerfChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Channel Performance',
                data: channels.map((ch, idx) => ({
                    x: conversionRates[idx],
                    y: attributionScores[idx],
                    label: ch
                })),
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                pointRadius: 8,
                pointHoverRadius: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Conversion Rate vs Attribution Score',
                    font: {
                        size: 18
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const channel = channels[context.dataIndex];
                            return `${channel}: Conv Rate ${context.parsed.x.toFixed(2)}%, Attribution ${context.parsed.y.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Conversion Rate (%)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Attribution Score (%)'
                    }
                }
            }
        }
    });
}

function setupChannelLimits(channels) {
    const container = document.getElementById('channelLimits');
    const limitsHTML = channels.map(channel => `
        <div class="channel-limit-item">
            <label>${channel}</label>
            <input type="number" 
                   id="limit_${channel.replace(/\s+/g, '_')}" 
                   placeholder="Max budget (optional)" 
                   min="0" 
                   step="100">
        </div>
    `).join('');
    
    container.innerHTML = `
        <h3>Channel Budget Limits</h3>
        <p class="help-text">Optional: Set maximum budget limits for each channel</p>
        ${limitsHTML}
    `;
}

// Optimize Budget
document.getElementById('optimizeBudget').addEventListener('click', async () => {
    if (!attributionResults) {
        alert('Please run attribution analysis first!');
        return;
    }
    
    const btn = document.getElementById('optimizeBudget');
    const btnText = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');
    
    btn.disabled = true;
    btnText.textContent = 'Optimizing...';
    loader.style.display = 'inline-block';
    
    try {
        const budget = parseFloat(document.getElementById('totalBudget').value);
        const channels = Object.keys(attributionResults);
        const channelLimits = {};
        
        channels.forEach(channel => {
            const limitInput = document.getElementById(`limit_${channel.replace(/\s+/g, '_')}`);
            if (limitInput && limitInput.value) {
                channelLimits[channel] = parseFloat(limitInput.value);
            }
        });
        
        const meanAttributions = {};
        channels.forEach(channel => {
            meanAttributions[channel] = attributionResults[channel]['Mean'];
        });
        
        const response = await fetch('/optimize_budget', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                budget: budget,
                channel_limits: channelLimits,
                mean_attributions: meanAttributions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayBudgetResults(data.allocations, budget);
            document.getElementById('budgetResultsSection').style.display = 'block';
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        alert('Error optimizing budget: ' + error);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Optimize Budget';
        loader.style.display = 'none';
    }
});

function displayBudgetResults(allocations, totalBudget) {
    const container = document.getElementById('budgetResults');
    
    const html = Object.entries(allocations).map(([channel, amount]) => `
        <div class="budget-item">
            <h3>${channel}</h3>
            <div class="amount">$${amount.toLocaleString()}</div>
            <div>${((amount / totalBudget) * 100).toFixed(1)}% of budget</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
    createBudgetChart(allocations);
}

function createBudgetChart(allocations) {
    const ctx = document.getElementById('budgetChart');
    
    if (budgetChart) {
        budgetChart.destroy();
    }
    
    const channels = Object.keys(allocations);
    const amounts = Object.values(allocations);
    
    budgetChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: channels,
            datasets: [{
                data: amounts,
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(118, 75, 162, 0.8)',
                    'rgba(17, 153, 142, 0.8)',
                    'rgba(56, 239, 125, 0.8)',
                    'rgba(255, 159, 64, 0.8)'
                ],
                borderColor: 'white',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Budget Distribution',
                    font: {
                        size: 18
                    }
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}
