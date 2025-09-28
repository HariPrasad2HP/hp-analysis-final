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
        
        // Load high contamination entities
        const highContaminationResponse = await fetch('/api/analysis/high-contamination');
        if (highContaminationResponse.ok) {
            const highContamination = await highContaminationResponse.json();
            console.log('High contamination data loaded:', highContamination.length, 'entities');
            updateHighContaminationTable(highContamination);
        } else {
            const errorData = await highContaminationResponse.json().catch(() => ({ error: 'Unknown error' }));
            console.error('Failed to load high contamination data:', errorData);
            showError('Failed to load high contamination data: ' + (errorData.error || 'Unknown error'));
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
    // Update key metric cards
    updateStatCard('total-nodes', summary.total_nodes || 0);
    updateStatCard('bogus-nodes', summary.bogus_nodes || 0);
    updateStatCard('contaminated-nodes', summary.contaminated_nodes || 0);
    updateStatCard('total-bogus-value', formatCurrency(summary.total_bogus_value || 0));
    updateStatCard('bogus-percentage', (summary.bogus_percentage || 0).toFixed(1) + '%');
    updateStatCard('total-purchases', formatCurrency(summary.total_purchases || 0));
}

function updateStatCard(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function createCharts(summary) {
    // Contamination Distribution Pie Chart
    if (summary.contamination_distribution) {
        createContaminationDistributionChart(summary.contamination_distribution);
    }
    
    // Bogus vs Normal Doughnut Chart
    createBogusChart(summary.bogus_nodes, summary.total_nodes - summary.bogus_nodes);
}

function createContaminationDistributionChart(contaminationData) {
    const ctx = document.getElementById('contaminationChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (window.contaminationChart && typeof window.contaminationChart.destroy === 'function') {
        window.contaminationChart.destroy();
    }
    
    const data = {
        labels: Object.keys(contaminationData),
        datasets: [{
            data: Object.values(contaminationData),
            backgroundColor: [
                '#2ecc71', // None - Green
                '#f39c12', // Low - Orange  
                '#e67e22', // Medium - Dark Orange
                '#e74c3c', // High - Red
                '#8e44ad'  // Very High - Purple
            ],
            borderWidth: 2,
            borderColor: '#fff'
        }]
    };
    
    window.contaminationChart = new Chart(ctx, {
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
                    text: 'Contamination Level Distribution'
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

function updateHighContaminationTable(highContaminationData) {
    const tbody = document.querySelector('#high-contamination-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!highContaminationData || highContaminationData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No high contamination entities found</td></tr>';
        return;
    }
    
    highContaminationData.slice(0, 10).forEach(entity => {
        const row = document.createElement('tr');
        const entityName = entity.Entity_Name || entity.PAN || 'N/A';
        const displayName = entityName.length > 30 ? entityName.substring(0, 30) + '...' : entityName;
        const status = entity.Is_Bogus ? 'BOGUS' : (entity.Is_Contaminated ? 'CONTAMINATED' : 'OK');
        const statusClass = entity.Is_Bogus ? 'status-bogus' : (entity.Is_Contaminated ? 'status-contaminated' : 'status-ok');
        
        row.innerHTML = `
            <td title="${entity.PAN}">${entity.PAN}</td>
            <td title="${entityName}">${displayName}</td>
            <td><span class="contamination-level contamination-${getContaminationLevel(entity.Contamination_Level)}">${(entity.Contamination_Level || 0).toFixed(1)}%</span></td>
            <td>${formatCurrency(entity.Bogus_Value || 0)}</td>
            <td>${(entity.Purchase_to_Sales_Ratio || 0).toFixed(3)}</td>
            <td><span class="status ${statusClass}">${status}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function getContaminationLevel(level) {
    if (level >= 80) return 'very-high';
    if (level >= 60) return 'high';
    if (level >= 40) return 'medium';
    if (level >= 20) return 'low';
    return 'none';
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
    console.error(message);
    
    // Create or update error display
    let errorDiv = document.getElementById('error-message');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'error-message';
        errorDiv.className = 'error-message';
        document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.summary-cards'));
    }
    
    errorDiv.innerHTML = `
        <div class="error-content">
            <span class="error-icon">⚠️</span>
            <span class="error-text">${message}</span>
            <button class="error-close" onclick="hideError()">×</button>
        </div>
    `;
    errorDiv.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(hideError, 10000);
}

function hideError() {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.style.display = 'none';
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
