// DAG Visualization JavaScript
let network;
let nodes, edges;
let allNodes = new vis.DataSet();
let allEdges = new vis.DataSet();
let visibleNodes = new vis.DataSet();
let visibleEdges = new vis.DataSet();

// Root node configuration - will be loaded from config
let ROOT_NODE_PAN = 'AAYCA4390A';  // Default, will be updated from config

document.addEventListener('DOMContentLoaded', function() {
    updateStatusIndicator('loading');
    loadGraphData();
});

// Update status indicator
function updateStatusIndicator(status) {
    const indicator = document.querySelector('.status-indicator');
    if (indicator) {
        indicator.className = `status-indicator ${status}`;
    }
}

function initializeNetwork() {
    const container = document.getElementById('mynetwork');
    
    // Create a DataSet with data
    nodes = visibleNodes;
    edges = visibleEdges;

    // Create a network
    const data = {
        nodes: nodes,
        edges: edges
    };
    
    const options = {
        nodes: {
            shape: 'dot',
            size: 20,
            font: {
                size: 12,
                color: '#000000'
            },
            borderWidth: 2,
            shadow: true
        },
        edges: {
            width: 2,
            color: {inherit: 'from'},
            smooth: {
                type: 'continuous'
            },
            arrows: {
                to: {enabled: true, scaleFactor: 1, type: 'arrow'}
            }
        },
        physics: {
            enabled: true,
            stabilization: {iterations: 100}
        },
        interaction: {
            hover: true,
            tooltipDelay: 200
        },
        layout: {
            hierarchical: {
                direction: 'UD',
                sortMethod: 'directed',
                levelSeparation: 100,
                nodeSpacing: 150
            }
        }
    };

    network = new vis.Network(container, data, options);
    
    // Add event listeners
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            toggleNodeChildren(nodeId);
        }
    });
    
    network.on('hoverNode', function(params) {
        showNodeTooltip(params.node);
    });
}

async function loadGraphData() {
    try {
        showLoading(true);
        updateStatusIndicator('loading');
        
        // Load configuration to get root node PAN
        const configResponse = await fetch('/api/config');
        if (configResponse.ok) {
            const config = await configResponse.json();
            ROOT_NODE_PAN = config.root_node_pan || 'AAYCA4390A';
            console.log(`Root node PAN set to: ${ROOT_NODE_PAN}`);
        }
        
        // Load the main data
        const response = await fetch('/api/data/gst_table_data.json');
        if (!response.ok) {
            throw new Error('Failed to load graph data');
        }
        
        const data = await response.json();
        processGraphData(data);
        
        // Initialize network
        initializeNetwork();
        
        // Show root node and its immediate children
        showRootChildren();
        
        // Update header description
        updateHeaderDescription();
        
        updateStats();
        updateStatusIndicator('online');
        showLoading(false);
        
    } catch (error) {
        console.error('Error loading graph data:', error);
        showError('Failed to load graph data: ' + error.message);
        updateStatusIndicator('offline');
        showLoading(false);
    }
}

function processGraphData(data) {
    // Clear existing data
    allNodes.clear();
    allEdges.clear();
    
    // Process nodes
    data.forEach(item => {
        const entityName = item.Entity_Name || item.PAN;
        const displayLabel = entityName.length > 12 ? entityName.substring(0, 12) + '...' : entityName;
        
        const node = {
            id: item.PAN,
            label: displayLabel,
            title: createNodeTooltip(item),
            color: getNodeColor(item),
            size: getNodeSize(item),
            data: item
        };
        allNodes.add(node);
    });
    
    // Process edges (relationships)
    data.forEach(item => {
        if (item.Children_PANs && item.Children_PANs.trim()) {
            const children = item.Children_PANs.split(',').map(c => c.trim());
            children.forEach(childPAN => {
                if (childPAN && allNodes.get(childPAN)) {
                    allEdges.add({
                        id: `${item.PAN}-${childPAN}`,
                        from: item.PAN,
                        to: childPAN
                    });
                }
            });
        }
    });
}

function createNodeTooltip(item) {
    const entityName = item.Entity_Name || item.PAN;
    return `
        <div style="padding: 10px; max-width: 300px;">
            <strong>Entity:</strong> ${entityName}<br>
            <strong>PAN:</strong> ${item.PAN}<br>
            <strong>Sales:</strong> ${formatCurrency(item.Total_Sales)}<br>
            <strong>Purchases:</strong> ${formatCurrency(item.Total_Purchases)}<br>
            <strong>P/S Ratio:</strong> ${(item.Purchase_to_Sales_Ratio || 0).toFixed(3)}<br>
            <strong>Risk Score:</strong> ${(item.Risk_Score || 0).toFixed(1)}<br>
            <strong>Status:</strong> ${item.Is_Bogus ? 'BOGUS' : 'OK'}<br>
            <strong>Transactions:</strong> ${item.Transaction_Count || 0}
        </div>
    `;
}

function getNodeColor(item) {
    if (item.PAN === ROOT_NODE_PAN) return '#667eea'; // Root node
    if (item.Is_Bogus) return '#f44336'; // Bogus
    if (item.Total_Purchases > 10000000) return '#9c27b0'; // High purchase
    return '#4caf50'; // OK
}

function getNodeSize(item) {
    const purchases = item.Total_Purchases || 0;
    if (purchases > 100000000) return 30;
    if (purchases > 10000000) return 25;
    if (purchases > 1000000) return 20;
    return 15;
}

function showRootChildren() {
    visibleNodes.clear();
    visibleEdges.clear();
    
    // Add root node (use dynamic root node from config)
    let rootNode = allNodes.get(ROOT_NODE_PAN);
    
    // If configured root node not found, try to find actual root nodes
    if (!rootNode) {
        console.warn(`Configured root node ${ROOT_NODE_PAN} not found in DAG data. Searching for actual root nodes...`);
        
        // Find nodes with no parents (actual root nodes)
        const allNodesArray = allNodes.get();
        const actualRootNodes = allNodesArray.filter(node => 
            !node.data.Parents_PANs || node.data.Parents_PANs.trim() === ''
        );
        
        if (actualRootNodes.length > 0) {
            rootNode = actualRootNodes[0];
            ROOT_NODE_PAN = rootNode.id;
            console.log(`Using actual root node found in DAG data: ${ROOT_NODE_PAN}`);
        }
    }
    
    if (rootNode) {
        visibleNodes.add(rootNode);
        
        // Add immediate children
        const rootEdges = allEdges.get({
            filter: function(edge) {
                return edge.from === ROOT_NODE_PAN;
            }
        });
        
        rootEdges.forEach(edge => {
            const childNode = allNodes.get(edge.to);
            if (childNode) {
                visibleNodes.add(childNode);
                visibleEdges.add(edge);
            }
        });
    }
    
    network.fit();
    updateStats();
}

function toggleNodeChildren(nodeId) {
    const currentChildren = visibleEdges.get({
        filter: function(edge) {
            return edge.from === nodeId;
        }
    });
    
    if (currentChildren.length > 0) {
        // Collapse - remove children
        collapseNode(nodeId);
    } else {
        // Expand - add children
        expandNode(nodeId);
    }
    
    updateStats();
}

function expandNode(nodeId) {
    const childEdges = allEdges.get({
        filter: function(edge) {
            return edge.from === nodeId;
        }
    });
    
    childEdges.forEach(edge => {
        const childNode = allNodes.get(edge.to);
        if (childNode && !visibleNodes.get(edge.to)) {
            visibleNodes.add(childNode);
            visibleEdges.add(edge);
        }
    });
}

function collapseNode(nodeId) {
    const childEdges = visibleEdges.get({
        filter: function(edge) {
            return edge.from === nodeId;
        }
    });
    
    childEdges.forEach(edge => {
        // Recursively collapse children
        collapseNode(edge.to);
        
        // Remove the child node and edge
        visibleNodes.remove(edge.to);
        visibleEdges.remove(edge.id);
    });
}

function expandAll() {
    visibleNodes.clear();
    visibleEdges.clear();
    
    // Add all nodes and edges (limit to prevent performance issues)
    const limitedNodes = allNodes.get().slice(0, 100);
    const limitedEdges = allEdges.get().slice(0, 200);
    
    visibleNodes.add(limitedNodes);
    visibleEdges.add(limitedEdges);
    
    network.fit();
    updateStats();
}

function collapseAll() {
    showRootChildren();
}

function fitToView() {
    network.fit();
}

function updateStats() {
    document.getElementById('visible-nodes').textContent = visibleNodes.length;
    document.getElementById('total-nodes').textContent = allNodes.length;
    document.getElementById('visible-edges').textContent = visibleEdges.length;
    
    // Count root children
    const rootChildren = allEdges.get({
        filter: function(edge) {
            return edge.from === ROOT_NODE_PAN;
        }
    }).length;
    document.getElementById('root-children').textContent = rootChildren;
}

function showNodeTooltip(nodeId) {
    const node = allNodes.get(nodeId);
    if (node && node.data) {
        // Tooltip is handled by vis.js title property
        console.log('Showing tooltip for:', nodeId);
    }
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

function showLoading(show) {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.style.display = show ? 'flex' : 'none';
    }
}

function showError(message) {
    console.error(message);
    const container = document.getElementById('mynetwork');
    container.innerHTML = `
        <div style="display: flex; justify-content: center; align-items: center; height: 100%; color: #f44336; font-size: 1.2em;">
            <div>
                <div style="margin-bottom: 10px;">⚠️ Error Loading Graph</div>
                <div style="font-size: 0.9em; color: #666;">${message}</div>
            </div>
        </div>
    `;
}

function updateHeaderDescription() {
    const headerDesc = document.getElementById('header-description');
    if (headerDesc) {
        const rootChildren = allEdges.get({
            filter: function(edge) {
                return edge.from === ROOT_NODE_PAN;
            }
        }).length;
        
        headerDesc.innerHTML = `
            <span class="status-indicator online"></span>
            Root Node: ${ROOT_NODE_PAN} → ${rootChildren} Direct Children → Expandable Purchase Hierarchy
        `;
    }
}

function toggleSidebar() {
    const sidebar = document.querySelector('.dag-sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    
    if (sidebar.classList.contains('hidden')) {
        sidebar.classList.remove('hidden');
        toggleBtn.textContent = '📋';
        toggleBtn.title = 'Hide Sidebar';
    } else {
        sidebar.classList.add('hidden');
        toggleBtn.textContent = '📊';
        toggleBtn.title = 'Show Sidebar';
    }
    
    // Resize network after sidebar toggle
    setTimeout(() => {
        if (network) {
            network.redraw();
            network.fit();
        }
    }, 300);
}
