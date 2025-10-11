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
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No high contamination entities found</td></tr>';
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
            <td><button class="show-sales-btn" onclick="showSalesRecords('${entity.PAN}', '${entityName.replace(/'/g, "\\'")}')">📋 Show Sales</button></td>
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

// Sales Records Modal Functions (shared with hierarchy.js)
async function showSalesRecords(pan, entityName) {
    try {
        console.log(`Fetching sales records for PAN: ${pan}`);
        
        // Show loading state
        showSalesModal(pan, entityName, [], true);
        
        // Fetch sales records from API
        const response = await fetch(`/api/sales/${pan}`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch sales records: ${response.status}`);
        }
        
        const data = await response.json();
        console.log(`Loaded ${data.total_sales_records} sales records for ${pan}`);
        
        // Show the modal with data
        showSalesModal(pan, entityName, data, false);
        
    } catch (error) {
        console.error('Error fetching sales records:', error);
        showSalesModal(pan, entityName, { error: error.message }, false);
    }
}

function showSalesModal(pan, entityName, data, isLoading) {
    // Remove existing modal if any
    const existingModal = document.getElementById('sales-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create modal HTML
    const modal = document.createElement('div');
    modal.id = 'sales-modal';
    modal.className = 'sales-modal';
    
    let modalContent = '';
    
    if (isLoading) {
        modalContent = `
            <div class="sales-modal-content">
                <div class="sales-modal-header">
                    <h3>📋 Sales Records - ${entityName}</h3>
                    <span class="sales-modal-close" onclick="closeSalesModal()">&times;</span>
                </div>
                <div class="sales-modal-body">
                    <div class="loading">Loading sales records...</div>
                </div>
            </div>
        `;
    } else if (data.error) {
        modalContent = `
            <div class="sales-modal-content">
                <div class="sales-modal-header">
                    <h3>📋 Sales Records - ${entityName}</h3>
                    <span class="sales-modal-close" onclick="closeSalesModal()">&times;</span>
                </div>
                <div class="sales-modal-body">
                    <div class="error">Error: ${data.error}</div>
                </div>
            </div>
        `;
    } else {
        const salesRecords = data.sales_records || [];
        const totalAmount = data.total_sales_amount || 0;
        
        let recordsHTML = '';
        if (salesRecords.length === 0) {
            recordsHTML = '<div class="no-records">No sales records found for this entity.</div>';
        } else {
            recordsHTML = `
                <div class="sales-summary">
                    <div class="summary-item">
                        <span class="summary-label">Total Sales Records:</span>
                        <span class="summary-value">${salesRecords.length}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Total Sales Amount:</span>
                        <span class="summary-value">${formatCurrency(totalAmount)}</span>
                    </div>
                </div>
                <div class="sales-controls">
                    <div class="sales-search">
                        <input type="text" id="sales-search" placeholder="🔍 Search by PAN, Name, or Business..." />
                    </div>
                    <div class="sales-filters">
                        <select id="taxpayer-filter">
                            <option value="">All Taxpayer Types</option>
                        </select>
                        <select id="amount-sort">
                            <option value="desc">Sort by Amount (High to Low)</option>
                            <option value="asc">Sort by Amount (Low to High)</option>
                            <option value="pan">Sort by PAN (A-Z)</option>
                            <option value="name">Sort by Name (A-Z)</option>
                        </select>
                        <button id="clear-filters" class="clear-filters-btn">Clear Filters</button>
                    </div>
                </div>
                <div class="sales-records-table">
                    <table id="sales-table">
                        <thead>
                            <tr>
                                <th data-sort="buyer_pan">Buyer PAN <span class="sort-indicator"></span></th>
                                <th data-sort="buyer_name">Buyer Name <span class="sort-indicator"></span></th>
                                <th data-sort="amount">Amount <span class="sort-indicator">↓</span></th>
                                <th data-sort="taxpayer_type">Taxpayer Type <span class="sort-indicator"></span></th>
                                <th data-sort="business_nature">Business Nature <span class="sort-indicator"></span></th>
                            </tr>
                        </thead>
                        <tbody id="sales-table-body">
                            <!-- Data will be populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
                <div class="sales-pagination">
                    <div class="pagination-info">
                        <span id="pagination-info">Showing <span id="showing-count">0</span> of <span id="total-count">0</span> records</span>
                    </div>
                    <div class="pagination-controls">
                        <button id="prev-page" class="pagination-btn">← Previous</button>
                        <span id="page-info">Page <span id="current-page">1</span> of <span id="total-pages">1</span></span>
                        <button id="next-page" class="pagination-btn">Next →</button>
                    </div>
                </div>
            `;
        }
        
        modalContent = `
            <div class="sales-modal-content">
                <div class="sales-modal-header">
                    <h3>📋 Sales Records - ${entityName}</h3>
                    <span class="sales-modal-close" onclick="closeSalesModal()">&times;</span>
                </div>
                <div class="sales-modal-body">
                    ${recordsHTML}
                </div>
            </div>
        `;
    }
    
    modal.innerHTML = modalContent;
    
    // Add click outside to close
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeSalesModal();
        }
    });
    
    // Add to body
    document.body.appendChild(modal);
    
    // Show modal
    setTimeout(() => {
        modal.classList.add('show');
        
        // Initialize sales table functionality if we have sales records
        if (!isLoading && !data.error && data.sales_records && data.sales_records.length > 0) {
            initializeSalesTable(data.sales_records);
        }
    }, 10);
}

function closeSalesModal() {
    const modal = document.getElementById('sales-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

// Sales Table Management (shared with hierarchy.js)
let currentSalesData = [];
let filteredSalesData = [];
let currentSortField = 'amount';
let currentSortDirection = 'desc';
let currentPage = 1;
const recordsPerPage = 10;

function initializeSalesTable(salesRecords) {
    console.log('Initializing sales table with records:', salesRecords);
    currentSalesData = [...salesRecords];
    filteredSalesData = [...salesRecords];
    
    // Populate taxpayer filter options
    populateTaxpayerFilter();
    
    // Sort by amount (high to low) by default
    sortSalesData('amount', 'desc');
    
    // Set up event listeners
    setupSalesTableEventListeners();
    
    // Initial render
    renderSalesTable();
    updatePaginationInfo();
    
    console.log('Sales table initialized with', filteredSalesData.length, 'records');
}

function populateTaxpayerFilter() {
    const taxpayerFilter = document.getElementById('taxpayer-filter');
    if (!taxpayerFilter) return;
    
    // Get unique taxpayer types
    const taxpayerTypes = [...new Set(currentSalesData.map(record => record.taxpayer_type).filter(type => type && type.trim()))];
    
    // Clear existing options (except "All")
    taxpayerFilter.innerHTML = '<option value="">All Taxpayer Types</option>';
    
    // Add unique taxpayer types
    taxpayerTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type.length > 30 ? type.substring(0, 30) + '...' : type;
        option.title = type;
        taxpayerFilter.appendChild(option);
    });
}

function setupSalesTableEventListeners() {
    // Search input
    const searchInput = document.getElementById('sales-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterSalesData();
        });
    }
    
    // Taxpayer filter
    const taxpayerFilter = document.getElementById('taxpayer-filter');
    if (taxpayerFilter) {
        taxpayerFilter.addEventListener('change', (e) => {
            filterSalesData();
        });
    }
    
    // Sort dropdown
    const amountSort = document.getElementById('amount-sort');
    if (amountSort) {
        amountSort.addEventListener('change', (e) => {
            const [field, direction] = e.target.value === 'desc' ? ['amount', 'desc'] :
                                     e.target.value === 'asc' ? ['amount', 'asc'] :
                                     e.target.value === 'pan' ? ['buyer_pan', 'asc'] :
                                     ['buyer_name', 'asc'];
            sortSalesData(field, direction);
        });
    }
    
    // Clear filters button
    const clearFilters = document.getElementById('clear-filters');
    if (clearFilters) {
        clearFilters.addEventListener('click', () => {
            clearSalesFilters();
        });
    }
    
    // Column header sorting
    const headers = document.querySelectorAll('#sales-table th[data-sort]');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const field = header.getAttribute('data-sort');
            const newDirection = (currentSortField === field && currentSortDirection === 'asc') ? 'desc' : 'asc';
            sortSalesData(field, newDirection);
            
            // Update sort dropdown to match
            const sortSelect = document.getElementById('amount-sort');
            if (sortSelect && field === 'amount') {
                sortSelect.value = newDirection;
            }
        });
    });
    
    // Pagination controls
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderSalesTable();
                updatePaginationInfo();
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const totalPages = Math.ceil(filteredSalesData.length / recordsPerPage);
            if (currentPage < totalPages) {
                currentPage++;
                renderSalesTable();
                updatePaginationInfo();
            }
        });
    }
}

function filterSalesData() {
    const searchTerm = document.getElementById('sales-search')?.value.toLowerCase() || '';
    const taxpayerFilter = document.getElementById('taxpayer-filter')?.value || '';
    
    filteredSalesData = currentSalesData.filter(record => {
        // Search filter
        const matchesSearch = !searchTerm || 
            record.buyer_pan.toLowerCase().includes(searchTerm) ||
            (record.buyer_name && record.buyer_name.toLowerCase().includes(searchTerm)) ||
            (record.business_nature && record.business_nature.toLowerCase().includes(searchTerm));
        
        // Taxpayer filter
        const matchesTaxpayer = !taxpayerFilter || record.taxpayer_type === taxpayerFilter;
        
        return matchesSearch && matchesTaxpayer;
    });
    
    // Reset to first page
    currentPage = 1;
    
    // Re-render table
    renderSalesTable();
    updatePaginationInfo();
}

function sortSalesData(field, direction) {
    currentSortField = field;
    currentSortDirection = direction;
    
    filteredSalesData.sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];
        
        // Handle different data types
        if (field === 'amount') {
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        } else {
            aVal = (aVal || '').toString().toLowerCase();
            bVal = (bVal || '').toString().toLowerCase();
        }
        
        let comparison = 0;
        if (aVal < bVal) comparison = -1;
        if (aVal > bVal) comparison = 1;
        
        return direction === 'desc' ? -comparison : comparison;
    });
    
    // Update sort indicators
    updateSortIndicators();
    
    // Re-render table
    renderSalesTable();
    updatePaginationInfo();
}

function updateSortIndicators() {
    // Clear all indicators
    document.querySelectorAll('.sort-indicator').forEach(indicator => {
        indicator.textContent = '';
    });
    
    // Set current indicator
    const currentHeader = document.querySelector(`th[data-sort="${currentSortField}"] .sort-indicator`);
    if (currentHeader) {
        currentHeader.textContent = currentSortDirection === 'asc' ? '↑' : '↓';
    }
}

function renderSalesTable() {
    const tbody = document.getElementById('sales-table-body');
    if (!tbody) return;
    
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = startIndex + recordsPerPage;
    const pageData = filteredSalesData.slice(startIndex, endIndex);
    
    tbody.innerHTML = pageData.map(record => `
        <tr>
            <td>${record.buyer_pan}</td>
            <td title="${record.buyer_name || record.buyer_pan}">${record.buyer_name || record.buyer_pan}</td>
            <td class="amount">${formatCurrency(record.amount)}</td>
            <td title="${record.taxpayer_type || '-'}">${(record.taxpayer_type || '-').length > 20 ? (record.taxpayer_type || '-').substring(0, 20) + '...' : (record.taxpayer_type || '-')}</td>
            <td title="${record.business_nature || '-'}">${(record.business_nature || '-').length > 30 ? (record.business_nature || '-').substring(0, 30) + '...' : (record.business_nature || '-')}</td>
        </tr>
    `).join('');
}

function updatePaginationInfo() {
    const totalRecords = filteredSalesData.length;
    const totalPages = Math.ceil(totalRecords / recordsPerPage);
    const startRecord = totalRecords > 0 ? (currentPage - 1) * recordsPerPage + 1 : 0;
    const endRecord = Math.min(currentPage * recordsPerPage, totalRecords);
    
    // Update counts
    document.getElementById('showing-count').textContent = totalRecords;
    document.getElementById('total-count').textContent = currentSalesData.length;
    document.getElementById('current-page').textContent = currentPage;
    document.getElementById('total-pages').textContent = totalPages;
    
    // Update pagination info
    document.getElementById('pagination-info').innerHTML = 
        `Showing ${startRecord}-${endRecord} of ${totalRecords} records`;
    
    // Update button states
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    if (prevBtn) prevBtn.disabled = currentPage <= 1;
    if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
}

function clearSalesFilters() {
    // Clear search
    const searchInput = document.getElementById('sales-search');
    if (searchInput) searchInput.value = '';
    
    // Clear taxpayer filter
    const taxpayerFilter = document.getElementById('taxpayer-filter');
    if (taxpayerFilter) taxpayerFilter.value = '';
    
    // Reset sort to default (amount desc)
    const sortSelect = document.getElementById('amount-sort');
    if (sortSelect) sortSelect.value = 'desc';
    
    // Reset data and re-render
    filteredSalesData = [...currentSalesData];
    currentPage = 1;
    sortSalesData('amount', 'desc');
}
