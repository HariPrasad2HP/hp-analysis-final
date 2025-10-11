// Hierarchy View JavaScript
let allData = [];
let panNames = {};
let availablePans = new Set();
let purchaseNodes = [];
let filteredNodes = [];
let expandedNodes = new Set();

// Root node configuration - will be loaded from config
let ROOT_NODE_PAN = 'AAYCA4390A';  // Default, will be updated from config
let rootChildrenPANs = [];  // Will be dynamically fetched from root file data

document.addEventListener('DOMContentLoaded', async function() {
    const contentEl = document.getElementById('content');
    
    try {
        console.log('Starting hierarchy data load...');
        
        // Load all required data
        console.log('Fetching data from APIs...');
        const [tableResponse, namesResponse, availabilityResponse, configResponse] = await Promise.all([
            fetch('/api/data/gst_table_data.json'),
            fetch('/api/data/pan_names.json'),
            fetch('/api/data/pan_availability.json'),
            fetch('/api/config')
        ]);
        
        console.log('API responses received:', {
            table: tableResponse.status,
            names: namesResponse.status,
            availability: availabilityResponse.status,
            config: configResponse.status
        });
        
        if (!tableResponse.ok) {
            throw new Error(`Failed to load table data: ${tableResponse.status}`);
        }
        
        allData = await tableResponse.json();
        console.log(`Loaded ${allData.length} records from table data`);
        
        // Load configuration to get root node PAN
        if (configResponse.ok) {
            const config = await configResponse.json();
            ROOT_NODE_PAN = config.root_node_pan || 'AAYCA4390A';
            console.log(`Root node PAN set to: ${ROOT_NODE_PAN}`);
        }
        
        // Ensure all numeric fields are properly converted from strings
        allData = allData.map(node => ({
            ...node,
            Total_Purchases: convertToNumber(node.Total_Purchases),
            Total_Sales: convertToNumber(node.Total_Sales),
            Purchase_to_Sales_Ratio: convertToNumber(node.Purchase_to_Sales_Ratio),
            Transaction_Count: convertToNumber(node.Transaction_Count),
            Avg_Transaction_Size: convertToNumber(node.Avg_Transaction_Size),
            Bogus_Value: convertToNumber(node.Bogus_Value),
            Contamination_Level: convertToNumber(node.Contamination_Level),
            Original_Total_Purchases: convertToNumber(node.Original_Total_Purchases),
            Adjusted_Purchases: convertToNumber(node.Adjusted_Purchases)
        }));
        
        // Load PAN names
        if (namesResponse.ok) {
            panNames = await namesResponse.json();
        }
        
        // Load PAN availability
        if (availabilityResponse.ok) {
            const availabilityData = await availabilityResponse.json();
            // Handle both array and object formats
            if (Array.isArray(availabilityData)) {
                availablePans = new Set(availabilityData);
            } else {
                // Object format: {PAN: boolean}
                availablePans = new Set(Object.keys(availabilityData).filter(pan => availabilityData[pan]));
            }
        }
        
        // Find the root node and extract its children dynamically
        let rootNode = allData.find(node => node.PAN === ROOT_NODE_PAN);
        
        if (!rootNode) {
            console.warn(`Configured root node ${ROOT_NODE_PAN} not found in data. Searching for actual root nodes...`);
            
            // Find nodes with no parents (actual root nodes)
            const actualRootNodes = allData.filter(node => 
                !node.Parents_PANs || node.Parents_PANs.trim() === ''
            );
            
            if (actualRootNodes.length > 0) {
                // Use the first available root node
                rootNode = actualRootNodes[0];
                ROOT_NODE_PAN = rootNode.PAN;
                console.log(`Using actual root node found in data: ${ROOT_NODE_PAN}`);
                
                // Update header to show the actual root node being used
                const headerDescription = document.getElementById('header-description');
                if (headerDescription) {
                    headerDescription.textContent = `Auto-detected Root Node: ${ROOT_NODE_PAN} → Dynamic Children → Expandable Hierarchy`;
                }
            } else {
                throw new Error(`No root nodes found in data. Expected root node ${ROOT_NODE_PAN} not found and no nodes with empty Parents_PANs exist.`);
            }
        }
        
        console.log('Root node details:', {
            PAN: rootNode.PAN,
            Purchases: formatCurrency(rootNode.Total_Purchases),
            Sales: formatCurrency(rootNode.Total_Sales),
            Children: rootNode.Children_PANs
        });
        
        // Extract children PANs from the root node data
        if (rootNode.Children_PANs && rootNode.Children_PANs.trim() !== '') {
            rootChildrenPANs = rootNode.Children_PANs.split(',').map(pan => pan.trim()).filter(pan => pan);
        } else {
            console.warn('Root node has no children defined in Children_PANs field');
            rootChildrenPANs = [];
        }
        
        // Get the children data from allData
        purchaseNodes = [];
        rootChildrenPANs.forEach(childPAN => {
            const childData = allData.find(node => node.PAN === childPAN);
            if (childData) {
                purchaseNodes.push(childData);
                console.log(`✓ Found child: ${childPAN} - Purchases: ${formatCurrency(childData.Total_Purchases)}`);
            } else {
                // Create placeholder for missing child data
                const placeholderData = {
                    PAN: childPAN,
                    Total_Sales: 0,
                    Total_Purchases: 0,
                    Purchase_to_Sales_Ratio: 0,
                    Is_Bogus: false,
                    Transaction_Count: 0,
                    Avg_Transaction_Size: 0,
                    Children_PANs: '',
                    Parents_PANs: rootNode.PAN,
                    _isMissing: true  // Flag to identify missing entries
                };
                purchaseNodes.push(placeholderData);
                console.warn(`✗ Child not found in data, created placeholder: ${childPAN}`);
            }
        });
        
        console.log(`Successfully loaded ${purchaseNodes.length} of ${rootChildrenPANs.length} root children`);
        
        // Sort by purchase amount descending
        purchaseNodes.sort((a, b) => b.Total_Purchases - a.Total_Purchases);
        
        // Update header description
        const headerDescription = document.getElementById('header-description');
        headerDescription.textContent = `Root Node: ${ROOT_NODE_PAN} → ${rootChildrenPANs.length} Direct Children → Expandable Hierarchy`;
        
        // Update section title
        const sectionTitle = document.getElementById('section-title');
        sectionTitle.textContent = `Children of Root Node ${ROOT_NODE_PAN} (${purchaseNodes.length})`;
        
        // Display purchase nodes
        filteredNodes = [...purchaseNodes];
        console.log('About to display nodes:', filteredNodes.length);
        displayPurchaseNodes(filteredNodes, contentEl);
        console.log('Hierarchy loading completed successfully');
        
    } catch (error) {
        contentEl.innerHTML = `
            <div class="error">
                <strong>Error:</strong> ${error.message}<br>
                <small>Check browser console for details</small>
            </div>
        `;
        console.error('Error loading data:', error);
    }
});

function convertToNumber(value) {
    if (value === null || value === undefined || value === '') return 0;
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
        // Remove commas and convert to number
        const cleaned = value.replace(/,/g, '');
        const num = parseFloat(cleaned);
        return isNaN(num) ? 0 : num;
    }
    return 0;
}

function formatCurrency(amount) {
    // Convert to number if needed
    const numAmount = convertToNumber(amount);
    
    if (!numAmount || numAmount === 0) return '₹0';
    
    // Indian currency formatting - crores and lakhs
    if (numAmount >= 1e7) { // 1 crore or more
        return `₹${(numAmount / 1e7).toFixed(2)} Cr`;
    }
    if (numAmount >= 1e5) { // 1 lakh or more
        return `₹${(numAmount / 1e5).toFixed(2)} L`;
    }
    if (numAmount >= 1e3) { // 1 thousand or more
        return `₹${(numAmount / 1e3).toFixed(1)}K`;
    }
    
    return `₹${Math.round(numAmount).toLocaleString('en-IN')}`;
}

function getPanName(panId, nodeData = null) {
    // First try to get from nodeData if available
    if (nodeData && nodeData.Entity_Name && nodeData.Entity_Name !== panId) {
        return nodeData.Entity_Name;
    }
    
    // Then try panNames mapping
    if (panNames[panId] && panNames[panId] !== 'Information Summary' && !panNames[panId].startsWith('Entity ')) {
        return panNames[panId];
    }
    
    // Fallback to Entity + PAN
    return `Entity ${panId}`;
}

function getPanStatus(panId) {
    return availablePans.has(panId) ? 'available' : 'missing';
}

function displayPurchaseNodes(nodes, container) {
    container.innerHTML = '';
    
    if (nodes.length === 0) {
        container.innerHTML = '<div class="loading">No purchase nodes match the current filters</div>';
        return;
    }
    
    nodes.forEach(nodeData => {
        const nodeEl = createPurchaseNodeElement(nodeData);
        container.appendChild(nodeEl);
    });
}

function createPurchaseNodeElement(nodeData) {
    const hasChildren = nodeData.Children_PANs && nodeData.Children_PANs !== null && nodeData.Children_PANs.trim() !== '';
    const children = hasChildren ? nodeData.Children_PANs.split(',').map(c => c.trim()).filter(c => c) : [];
    
    const nodeDiv = document.createElement('div');
    nodeDiv.className = 'node';
    
    const ratio = nodeData.Purchase_to_Sales_Ratio;
    const displayRatio = ratio === null ? '∞' : ratio.toFixed(3);
    
    // Determine node status
    const panStatus = getPanStatus(nodeData.PAN);
    const isBogus = nodeData.Is_Bogus;
    const isMissing = panStatus === 'missing' || nodeData._isMissing;
    
    let statusClass, statusText;
    if (isMissing) {
        statusClass = 'missing';
        statusText = nodeData._isMissing ? 'NO DATA FILE' : 'MISSING FILE';
    } else if (isBogus) {
        statusClass = 'bogus';
        statusText = 'BOGUS';
    } else if (nodeData.Is_Contaminated) {
        statusClass = 'contaminated';
        statusText = 'CONTAMINATED';
    } else {
        statusClass = 'ok';
        statusText = 'OK';
    }
    
    const panName = getPanName(nodeData.PAN, nodeData);
    const opacityStyle = nodeData._isMissing ? 'style="opacity: 0.6;"' : '';
    
    nodeDiv.innerHTML = `
        <div class="node-header purchase-node ${statusClass}" ${opacityStyle}>
            <div class="node-left">
                <span class="toggle-btn">${hasChildren ? '[+]' : '•'}</span>
                <div class="node-identity">
                    <div class="node-name">${panName}</div>
                    <div class="node-pan">${nodeData.PAN}</div>
                </div>
            </div>
            <div class="node-metrics">
                <div class="metric">
                    <span class="metric-label">Purchase Value</span>
                    <span class="metric-value purchase">${formatCurrency(nodeData.Total_Purchases)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Sales Value</span>
                    <span class="metric-value sales">${formatCurrency(nodeData.Total_Sales)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">P/S Ratio</span>
                    <span class="metric-value">${displayRatio}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Bogus Purchases</span>
                    <span class="metric-value bogus-value">${formatCurrency(nodeData.Bogus_Value || 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Contamination</span>
                    <span class="metric-value contamination">${nodeData.Is_Contaminated ? nodeData.Contamination_Level.toFixed(1) + '%' : '0%'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value ${statusClass}">${statusText}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Children</span>
                    <span class="metric-value">${children.length}</span>
                </div>
                <div class="metric">
                    <button class="show-sales-btn" onclick="showSalesRecords('${nodeData.PAN}', '${panName.replace(/'/g, "\\'")}')">
                        📋 Show Sales
                    </button>
                </div>
            </div>
        </div>
    `;
    
    if (hasChildren) {
        const childrenDiv = document.createElement('div');
        childrenDiv.className = 'children';
        nodeDiv.appendChild(childrenDiv);
        
        const header = nodeDiv.querySelector('.node-header');
        const toggleBtn = header.querySelector('.toggle-btn');
        
        header.addEventListener('click', () => {
            const isExpanded = expandedNodes.has(nodeData.PAN);
            
            if (isExpanded) {
                // Collapse
                childrenDiv.classList.remove('expanded');
                childrenDiv.innerHTML = '';
                toggleBtn.textContent = '[+]';
                expandedNodes.delete(nodeData.PAN);
            } else {
                // Expand
                childrenDiv.innerHTML = '<div class="loading" style="padding: 20px;">Loading children...</div>';
                childrenDiv.classList.add('expanded');
                toggleBtn.textContent = '[-]';
                expandedNodes.add(nodeData.PAN);
                
                // Load children with delay
                setTimeout(() => {
                    loadChildren(children, childrenDiv);
                }, 50);
            }
        });
    }
    
    return nodeDiv;
}

function loadChildren(childrenPANs, container) {
    container.innerHTML = '';
    
    childrenPANs.forEach(childPAN => {
        const childData = allData.find(n => n.PAN === childPAN);
        if (childData) {
            // Only show children that also have purchases (to maintain purchase hierarchy)
            if (childData.Total_Purchases > 0) {
                container.appendChild(createPurchaseNodeElement(childData));
            } else {
                // Show non-purchase children with limited info
                const placeholder = createNonPurchaseChild(childPAN, childData);
                container.appendChild(placeholder);
            }
        } else {
            // Create placeholder for missing child data
            const placeholder = createMissingChild(childPAN);
            container.appendChild(placeholder);
        }
    });
}

function createNonPurchaseChild(childPAN, childData) {
    const panStatus = getPanStatus(childPAN);
    const statusClass = childData.Is_Bogus ? 'bogus' : 'ok';
    const statusText = childData.Is_Bogus ? 'BOGUS' : 'OK';
    
    const div = document.createElement('div');
    div.innerHTML = `
        <div class="node">
            <div class="node-header ${statusClass}" style="opacity: 0.7;">
                <div class="node-left">
                    <span class="toggle-btn">•</span>
                    <div class="node-identity">
                        <div class="node-name">${getPanName(childPAN, childData)}</div>
                        <div class="node-pan">${childPAN}</div>
                    </div>
                </div>
                <div class="node-metrics">
                    <div class="metric">
                        <span class="metric-label">Purchase Value</span>
                        <span class="metric-value">₹0</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Sales Value</span>
                        <span class="metric-value sales">${formatCurrency(childData.Total_Sales)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Bogus Value</span>
                        <span class="metric-value bogus-value">${formatCurrency(childData.Bogus_Value || 0)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Status</span>
                        <span class="metric-value ${statusClass}">${statusText}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Note</span>
                        <span class="metric-value">Sales Only</span>
                    </div>
                    <div class="metric">
                        <button class="show-sales-btn" onclick="showSalesRecords('${childPAN}', '${getPanName(childPAN, childData).replace(/'/g, "\\'")}')">
                            📋 Show Sales
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    return div;
}

function createMissingChild(childPAN) {
    const panStatus = getPanStatus(childPAN);
    const statusClass = panStatus === 'missing' ? 'missing' : 'ok';
    const statusText = panStatus === 'missing' ? 'MISSING FILE' : 'NOT IN ANALYSIS';
    
    const div = document.createElement('div');
    div.innerHTML = `
        <div class="node">
            <div class="node-header ${statusClass}" style="opacity: 0.6;">
                <div class="node-left">
                    <span class="toggle-btn">•</span>
                    <div class="node-identity">
                        <div class="node-name">${getPanName(childPAN)}</div>
                        <div class="node-pan">${childPAN}</div>
                    </div>
                </div>
                <div class="node-metrics">
                    <div class="metric">
                        <span class="metric-label">Status</span>
                        <span class="metric-value ${statusClass}">${statusText}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Data</span>
                        <span class="metric-value">N/A</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    return div;
}

function applyFilters() {
    const minPurchase = parseFloat(document.getElementById('minPurchase').value) || 0;
    const minSales = parseFloat(document.getElementById('minSales').value) || 0;
    const statusFilter = document.getElementById('statusFilter').value;
    
    filteredNodes = purchaseNodes.filter(node => {
        // Purchase filter
        if (node.Total_Purchases < minPurchase) return false;
        
        // Sales filter
        if (node.Total_Sales < minSales) return false;
        
        // Status filter
        if (statusFilter) {
            const panStatus = getPanStatus(node.PAN);
            const isBogus = node.Is_Bogus;
            const isMissing = panStatus === 'missing';
            
            if (statusFilter === 'bogus' && !isBogus) return false;
            if (statusFilter === 'ok' && (isBogus || isMissing)) return false;
            if (statusFilter === 'missing' && !isMissing) return false;
        }
        
        return true;
    });
    
    // Update section title
    const sectionTitle = document.getElementById('section-title');
    sectionTitle.textContent = `Filtered Purchase Entries (${filteredNodes.length} of ${purchaseNodes.length})`;
    
    // Display filtered nodes
    const contentEl = document.getElementById('content');
    displayPurchaseNodes(filteredNodes, contentEl);
    
    console.log(`Applied filters: ${filteredNodes.length} nodes match criteria`);
}

function clearFilters() {
    document.getElementById('panSearch').value = '';
    document.getElementById('minPurchase').value = '';
    document.getElementById('minSales').value = '';
    document.getElementById('statusFilter').value = '';
    
    filteredNodes = [...purchaseNodes];
    
    // Update section title
    const sectionTitle = document.getElementById('section-title');
    sectionTitle.textContent = `Children of Root Node ${ROOT_NODE_PAN} (${purchaseNodes.length})`;
    
    // Display all nodes
    const contentEl = document.getElementById('content');
    displayPurchaseNodes(filteredNodes, contentEl);
    
    console.log('Filters cleared, showing all purchase nodes');
}

// PAN Search Functionality
function searchPAN() {
    const searchTerm = document.getElementById('panSearch').value.trim();
    
    if (!searchTerm) {
        alert('Please enter a PAN number or entity name to search');
        return;
    }
    
    console.log(`Searching for PAN: ${searchTerm}`);
    
    // Search in all data (not just purchase nodes)
    const searchResults = allData.filter(node => {
        const panMatch = node.PAN && node.PAN.toLowerCase().includes(searchTerm.toLowerCase());
        const nameMatch = node.Entity_Name && node.Entity_Name.toLowerCase().includes(searchTerm.toLowerCase());
        return panMatch || nameMatch;
    });
    
    console.log(`Found ${searchResults.length} matching entities`);
    
    if (searchResults.length === 0) {
        alert(`No entities found matching "${searchTerm}"`);
        return;
    }
    
    // Display search results
    displaySearchResults(searchResults, searchTerm);
}

function displaySearchResults(results, searchTerm) {
    const contentEl = document.getElementById('content');
    const sectionTitle = document.getElementById('section-title');
    
    // Update section title
    sectionTitle.textContent = `Search Results for "${searchTerm}" (${results.length} found)`;
    
    if (results.length === 1) {
        // Single result - show detailed view with hierarchy
        const entity = results[0];
        showEntityDetails(entity);
    } else {
        // Multiple results - show list view
        contentEl.innerHTML = '';
        
        results.forEach(entity => {
            const entityDiv = createSearchResultNode(entity, searchTerm);
            contentEl.appendChild(entityDiv);
        });
    }
}

function createSearchResultNode(nodeData, searchTerm) {
    const nodeDiv = document.createElement('div');
    nodeDiv.className = 'node search-result';
    
    const panName = nodeData.Entity_Name || nodeData.PAN;
    const statusClass = nodeData.Is_Bogus ? 'bogus' : 'ok';
    const statusText = nodeData.Is_Bogus ? 'BOGUS' : 'OK';
    
    // Highlight search term in PAN and name
    const highlightedPAN = highlightSearchTerm(nodeData.PAN, searchTerm);
    const highlightedName = highlightSearchTerm(panName, searchTerm);
    
    nodeDiv.innerHTML = `
        <div class="node-header ${statusClass}">
            <div class="node-left">
                <span class="toggle-btn">🔍</span>
                <div class="node-identity">
                    <div class="node-name">${highlightedName}</div>
                    <div class="node-pan">${highlightedPAN}</div>
                </div>
            </div>
            <div class="node-metrics">
                <div class="metric">
                    <span class="metric-label">Purchase Value</span>
                    <span class="metric-value purchase">${formatCurrency(nodeData.Total_Purchases)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Sales Value</span>
                    <span class="metric-value sales">${formatCurrency(nodeData.Total_Sales)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">P/S Ratio</span>
                    <span class="metric-value">${nodeData.Purchase_to_Sales_Ratio ? nodeData.Purchase_to_Sales_Ratio.toFixed(3) : 'N/A'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value ${statusClass}">${statusText}</span>
                </div>
                <div class="metric">
                    <button class="show-sales-btn" onclick="showSalesRecords('${nodeData.PAN}', '${panName.replace(/'/g, "\\'")}')">
                        📋 Show Sales
                    </button>
                </div>
                <div class="metric">
                    <button class="view-details-btn" onclick="showEntityDetails('${nodeData.PAN}')">
                        📊 View Details
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return nodeDiv;
}

function highlightSearchTerm(text, searchTerm) {
    if (!text || !searchTerm) return text || '';
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.replace(regex, '<mark class="search-highlight">$1</mark>');
}

function showEntityDetails(panOrEntity) {
    let entity;
    
    if (typeof panOrEntity === 'string') {
        // PAN string provided, find the entity
        entity = allData.find(node => node.PAN === panOrEntity);
        if (!entity) {
            alert(`Entity with PAN ${panOrEntity} not found`);
            return;
        }
    } else {
        // Entity object provided
        entity = panOrEntity;
    }
    
    const contentEl = document.getElementById('content');
    const sectionTitle = document.getElementById('section-title');
    
    // Update section title
    sectionTitle.textContent = `Entity Details: ${entity.Entity_Name || entity.PAN}`;
    
    // Create detailed view
    contentEl.innerHTML = `
        <div class="entity-details">
            <div class="entity-header">
                <h2>${entity.Entity_Name || entity.PAN}</h2>
                <p class="entity-pan">PAN: ${entity.PAN}</p>
            </div>
            
            <div class="entity-metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Financial Overview</div>
                    <div class="metric-row">
                        <span class="metric-label">Total Sales:</span>
                        <span class="metric-value sales">${formatCurrency(entity.Total_Sales)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Total Purchases:</span>
                        <span class="metric-value purchase">${formatCurrency(entity.Total_Purchases)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">P/S Ratio:</span>
                        <span class="metric-value">${entity.Purchase_to_Sales_Ratio ? entity.Purchase_to_Sales_Ratio.toFixed(3) : 'N/A'}</span>
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Risk Assessment</div>
                    <div class="metric-row">
                        <span class="metric-label">Status:</span>
                        <span class="metric-value ${entity.Is_Bogus ? 'bogus' : 'ok'}">${entity.Is_Bogus ? 'BOGUS' : 'OK'}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Bogus Value:</span>
                        <span class="metric-value bogus-value">${formatCurrency(entity.Bogus_Value || 0)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Contamination:</span>
                        <span class="metric-value contamination">${entity.Is_Contaminated ? entity.Contamination_Level.toFixed(1) + '%' : '0%'}</span>
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-title">Relationships</div>
                    <div class="metric-row">
                        <span class="metric-label">Children:</span>
                        <span class="metric-value">${entity.Children_PANs ? entity.Children_PANs.split(',').length : 0}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Parents:</span>
                        <span class="metric-value">${entity.Parents_PANs ? entity.Parents_PANs.split(',').length : 0}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Transaction Count:</span>
                        <span class="metric-value">${entity.Transaction_Count || 0}</span>
                    </div>
                </div>
            </div>
            
            <div class="entity-actions">
                <button class="action-btn primary" onclick="showSalesRecords('${entity.PAN}', '${(entity.Entity_Name || entity.PAN).replace(/'/g, "\\'")}')">
                    📋 View Sales Records
                </button>
                <button class="action-btn secondary" onclick="showEntityInHierarchy('${entity.PAN}')">
                    🌳 Show in Hierarchy
                </button>
                <button class="action-btn secondary" onclick="loadHierarchyView()">
                    ← Back to Hierarchy
                </button>
            </div>
        </div>
    `;
}

function showEntityInHierarchy(pan) {
    // Check if the entity is in the current purchase nodes
    const entityInPurchaseNodes = purchaseNodes.find(node => node.PAN === pan);
    
    if (entityInPurchaseNodes) {
        // Entity is in current hierarchy, scroll to it
        loadHierarchyView();
        setTimeout(() => {
            const entityElement = document.querySelector(`[data-pan="${pan}"]`);
            if (entityElement) {
                entityElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                entityElement.classList.add('highlight-entity');
                setTimeout(() => {
                    entityElement.classList.remove('highlight-entity');
                }, 3000);
            }
        }, 500);
    } else {
        alert(`Entity ${pan} is not in the current purchase hierarchy. It may be a sales-only entity or not directly connected to the root node.`);
    }
}

// Add keyboard support for search
document.addEventListener('DOMContentLoaded', function() {
    const panSearchInput = document.getElementById('panSearch');
    if (panSearchInput) {
        panSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchPAN();
            }
        });
        
        // Real-time search as user types (optional)
        panSearchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.trim();
            if (searchTerm.length >= 3) {
                // Show search suggestions or live results
                showSearchSuggestions(searchTerm);
            }
        });
    }
});

function showSearchSuggestions(searchTerm) {
    // Find matching entities
    const matches = allData.filter(node => {
        const panMatch = node.PAN && node.PAN.toLowerCase().includes(searchTerm.toLowerCase());
        const nameMatch = node.Entity_Name && node.Entity_Name.toLowerCase().includes(searchTerm.toLowerCase());
        return panMatch || nameMatch;
    }).slice(0, 5); // Limit to 5 suggestions
    
    // Create or update suggestions dropdown
    let suggestionsDiv = document.getElementById('pan-search-suggestions');
    if (!suggestionsDiv) {
        suggestionsDiv = document.createElement('div');
        suggestionsDiv.id = 'pan-search-suggestions';
        suggestionsDiv.className = 'search-suggestions';
        document.getElementById('panSearch').parentNode.appendChild(suggestionsDiv);
    }
    
    if (matches.length > 0) {
        suggestionsDiv.innerHTML = matches.map(entity => `
            <div class="suggestion-item" onclick="selectSearchSuggestion('${entity.PAN}', '${(entity.Entity_Name || entity.PAN).replace(/'/g, "\\'")}')">
                <div class="suggestion-pan">${entity.PAN}</div>
                <div class="suggestion-name">${entity.Entity_Name || 'No Name'}</div>
            </div>
        `).join('');
        suggestionsDiv.style.display = 'block';
    } else {
        suggestionsDiv.style.display = 'none';
    }
}

function selectSearchSuggestion(pan, name) {
    document.getElementById('panSearch').value = pan;
    document.getElementById('pan-search-suggestions').style.display = 'none';
    searchPAN();
}

function loadHierarchyView() {
    // Reset to hierarchy view
    const contentEl = document.getElementById('content');
    const sectionTitle = document.getElementById('section-title');
    
    // Update section title
    sectionTitle.textContent = `Children of Root Node ${ROOT_NODE_PAN} (${purchaseNodes.length})`;
    
    // Display purchase nodes
    displayPurchaseNodes(filteredNodes.length > 0 ? filteredNodes : purchaseNodes, contentEl);
    
    // Clear search input
    document.getElementById('panSearch').value = '';
    
    // Hide suggestions if visible
    const suggestionsDiv = document.getElementById('pan-search-suggestions');
    if (suggestionsDiv) {
        suggestionsDiv.style.display = 'none';
    }
}

// Sales Records Modal Functions
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

// Sales Table Management
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
    console.log('Rendering sales table...');
    const tbody = document.getElementById('sales-table-body');
    if (!tbody) {
        console.error('Sales table body not found!');
        return;
    }
    
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = startIndex + recordsPerPage;
    const pageData = filteredSalesData.slice(startIndex, endIndex);
    
    console.log('Rendering', pageData.length, 'records for page', currentPage);
    
    tbody.innerHTML = pageData.map(record => `
        <tr>
            <td>${record.buyer_pan}</td>
            <td title="${record.buyer_name || record.buyer_pan}">${record.buyer_name || record.buyer_pan}</td>
            <td class="amount">${formatCurrency(record.amount)}</td>
            <td title="${record.taxpayer_type || '-'}">${(record.taxpayer_type || '-').length > 20 ? (record.taxpayer_type || '-').substring(0, 20) + '...' : (record.taxpayer_type || '-')}</td>
            <td title="${record.business_nature || '-'}">${(record.business_nature || '-').length > 30 ? (record.business_nature || '-').substring(0, 30) + '...' : (record.business_nature || '-')}</td>
        </tr>
    `).join('');
    
    console.log('Table rendered with HTML length:', tbody.innerHTML.length);
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
