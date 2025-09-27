// Dashboard JavaScript
let isLoading = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    
    // Show initial loading state
    showLoading(true);
    
    // Load dashboard data
    loadDashboardData();
    
    // Set up periodic refresh (but not too frequent to avoid continuous loading)
    setInterval(() => {
        if (!isLoading) {
            loadDashboardData();
        }
    }, 60000); // Refresh every 60 seconds
});

async function loadDashboardData() {
    if (isLoading) return; // Prevent multiple simultaneous loads
    
    try {
        isLoading = true;
        console.log('Loading dashboard data...');
        
        // Load summary statistics
        const summaryResponse = await fetch('/api/analysis/summary');
        if (summaryResponse.ok) {
            const summary = await summaryResponse.json();
            console.log('Summary data loaded:', summary);
            updateSummaryStats(summary);
            createCharts(summary);
        } else {
            const errorData = await summaryResponse.json().catch(() => ({ error: 'Unknown error' }));
            console.error('Failed to load summary data:', errorData);
            showError('Failed to load summary data: ' + (errorData.error || 'Unknown error'));
        }
        
        // Load high risk entities
        const highRiskResponse = await fetch('/api/analysis/high-risk');
        if (highRiskResponse.ok) {
            const highRisk = await highRiskResponse.json();
            console.log('High risk data loaded:', highRisk.length, 'entities');
            updateHighRiskTable(highRisk);
        } else {
            const errorData = await highRiskResponse.json().catch(() => ({ error: 'Unknown error' }));
            console.error('Failed to load high risk data:', errorData);
            showError('Failed to load high risk data: ' + (errorData.error || 'Unknown error'));
        }
        
        // Hide loading state
        showLoading(false);
        console.log('Dashboard data loading completed');
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError('Error loading dashboard data: ' + error.message);
        showLoading(false);
    } finally {
        isLoading = false;
    }
}

function updateSummaryStats(summary) {
    // Update stat cards
    updateStatCard('total-nodes', summary.total_nodes || 0);
    updateStatCard('bogus-nodes', summary.bogus_nodes || 0);
    updateStatCard('bogus-percentage', (summary.bogus_percentage || 0).toFixed(1) + '%');
    updateStatCard('high-risk-nodes', summary.high_risk_nodes || 0);
    updateStatCard('total-sales', formatCurrency(summary.total_sales || 0));
    updateStatCard('total-purchases', formatCurrency(summary.total_purchases || 0));
    updateStatCard('ps-ratio', (summary.overall_ps_ratio || 0).toFixed(3));
}

function updateStatCard(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function createCharts(summary) {
    // Risk Distribution Pie Chart
    if (summary.risk_distribution) {
        createRiskDistributionChart(summary.risk_distribution);
    }
    
    // Bogus vs Normal Doughnut Chart
    createBogusChart(summary.bogus_nodes, summary.total_nodes - summary.bogus_nodes);
}

function createRiskDistributionChart(riskData) {
    const ctx = document.getElementById('riskChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (window.riskChart && typeof window.riskChart.destroy === 'function') {
        window.riskChart.destroy();
    }
    
    const data = {
        labels: Object.keys(riskData),
        datasets: [{
            data: Object.values(riskData),
            backgroundColor: [
                '#2ecc71', // Very Low - Green
                '#f39c12', // Low - Orange  
                '#e67e22', // Medium - Dark Orange
                '#e74c3c', // High - Red
                '#8e44ad'  // Very High - Purple
            ],
            borderWidth: 2,
            borderColor: '#fff'
        }]
    };
    
    window.riskChart = new Chart(ctx, {
        type: 'pie',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: 'Risk Score Distribution'
                }
            }
        }
    });
}

function createBogusChart(bogusCount, normalCount) {
    const ctx = document.getElementById('bogusChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (window.bogusChart && typeof window.bogusChart.destroy === 'function') {
        window.bogusChart.destroy();
    }
    
    const data = {
        labels: ['Bogus Transactions', 'Normal Transactions'],
        datasets: [{
            data: [bogusCount, normalCount],
            backgroundColor: ['#e74c3c', '#2ecc71'],
            borderWidth: 2,
            borderColor: '#fff'
        }]
    };
    
    window.bogusChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: 'Transaction Status'
                }
            }
        }
    });
}

function updateHighRiskTable(highRiskData) {
    const tbody = document.querySelector('#high-risk-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!highRiskData || highRiskData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No high risk entities found</td></tr>';
        return;
    }
    
    highRiskData.slice(0, 10).forEach(entity => {
        const row = document.createElement('tr');
        const entityName = entity.Entity_Name || entity.PAN || 'N/A';
        const displayName = entityName.length > 30 ? entityName.substring(0, 30) + '...' : entityName;
        
        row.innerHTML = `
            <td title="${entityName}">${displayName}</td>
            <td>${formatCurrency(entity.Total_Sales || 0)}</td>
            <td>${formatCurrency(entity.Total_Purchases || 0)}</td>
            <td>${(entity.Purchase_to_Sales_Ratio || 0).toFixed(3)}</td>
            <td><span class="risk-score risk-${getRiskLevel(entity.Risk_Score)}">${(entity.Risk_Score || 0).toFixed(1)}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function getRiskLevel(score) {
    if (score >= 80) return 'very-high';
    if (score >= 60) return 'high';
    if (score >= 40) return 'medium';
    if (score >= 20) return 'low';
    return 'very-low';
}

function formatCurrency(amount) {
    if (amount === 0) return '₹0';
    if (amount >= 10000000) {
        return '₹' + (amount / 10000000).toFixed(1) + 'Cr';
    } else if (amount >= 100000) {
        return '₹' + (amount / 100000).toFixed(1) + 'L';
    } else if (amount >= 1000) {
        return '₹' + (amount / 1000).toFixed(1) + 'K';
    }
    return '₹' + amount.toLocaleString('en-IN');
}

function showError(message) {
    console.error('Dashboard error:', message);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.style.cssText = 'background: #fee; color: #c33; padding: 15px; border-radius: 8px; margin: 20px; border: 1px solid #fcc;';
    errorDiv.textContent = message;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
        
        // Remove error after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
}

function showLoading(show) {
    // Use the existing loading overlay from the HTML template
    const loadingOverlay = document.getElementById('loading');
    
    if (loadingOverlay) {
        if (show) {
            loadingOverlay.style.display = 'flex';
        } else {
            loadingOverlay.style.display = 'none';
        }
    } else {
        console.warn('Loading overlay element not found');
    }
}
