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
