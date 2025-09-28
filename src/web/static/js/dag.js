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
                size: 13,
                color: '#333333',
                face: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                strokeWidth: 2,
                strokeColor: '#ffffff'
            },
            borderWidth: 3,
            shadow: {
                enabled: true,
                color: 'rgba(0,0,0,0.2)',
                size: 8,
                x: 2,
                y: 2
            },
            scaling: {
                min: 15,
                max: 40
            }
        },
        edges: {
            width: 3,
            color: {
                color: '#848484',
                highlight: '#667eea',
                hover: '#667eea'
            },
            smooth: {
                enabled: true,
                type: 'dynamic',
                roundness: 0.5
            },
            arrows: {
                to: {
                    enabled: true, 
                    scaleFactor: 1.2, 
                    type: 'arrow'
                }
            },
            shadow: {
                enabled: true,
                color: 'rgba(0,0,0,0.1)',
                size: 5,
                x: 1,
                y: 1
            }
        },
        physics: {
            enabled: true,
            stabilization: {
                iterations: 150,
                updateInterval: 25
            },
            barnesHut: {
                gravitationalConstant: -8000,
                centralGravity: 0.3,
                springLength: 120,
                springConstant: 0.04,
                damping: 0.09,
                avoidOverlap: 0.1
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 0,
            hideEdgesOnDrag: false,
            hideNodesOnDrag: false
        },
        configure: {
            enabled: false
        },
        layout: {
            hierarchical: {
                enabled: true,
                direction: 'UD',
                sortMethod: 'directed',
                levelSeparation: 120,
                nodeSpacing: 180,
                treeSpacing: 200,
                blockShifting: true,
                edgeMinimization: true,
                parentCentralization: true
            }
        }
    };

    network = new vis.Network(container, data, options);
    
    // Create custom tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.style.cssText = `
        position: absolute;
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 350px;
        z-index: 1000;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
        display: none;
    `;
    container.appendChild(tooltip);
    
    // Add event listeners
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            toggleNodeChildren(nodeId);
        }
    });
    
    network.on('hoverNode', function(params) {
        showCustomTooltip(params.node, params.event);
    });
    
    network.on('blurNode', function(params) {
        hideCustomTooltip();
    });
    
    // Hide tooltip when mouse leaves the network
    container.addEventListener('mouseleave', hideCustomTooltip);
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
    const status = getNodeStatus(item);
    const statusClass = status.toLowerCase().replace(' ', '-');
    
    // Create clean HTML without embedded HTML elements
    const tooltipHTML = `
        <div class="tooltip-header">
            ${entityName}
        </div>
        <div class="tooltip-body">
            <div class="tooltip-row">
                <span class="tooltip-label">PAN:</span>
                <span class="tooltip-value">${item.PAN}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Sales:</span>
                <span class="tooltip-value">${formatCurrency(item.Total_Sales || 0)}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Purchases:</span>
                <span class="tooltip-value">${formatCurrency(item.Total_Purchases || 0)}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Bogus Purchases:</span>
                <span class="tooltip-value">${formatCurrency(item.Bogus_Value || 0)}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">P/S Ratio:</span>
                <span class="tooltip-value">${(item.Purchase_to_Sales_Ratio || 0).toFixed(3)}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Contamination:</span>
                <span class="tooltip-value">${(item.Contamination_Level || 0).toFixed(1)}%</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Transactions:</span>
                <span class="tooltip-value">${item.Transaction_Count || 0}</span>
            </div>
            <div class="tooltip-row">
                <span class="tooltip-label">Status:</span>
                <span class="tooltip-status ${statusClass}">${status}</span>
            </div>
        </div>
    `;
    
    return tooltipHTML;
}

function getNodeColor(item) {
    // Root node - special blue gradient
    if (item.PAN === ROOT_NODE_PAN) {
        return {
            background: '#667eea',
            border: '#5a6fd8',
            highlight: {
                background: '#5a6fd8',
                border: '#4c63d2'
            }
        };
    }
    
    // Bogus nodes - red gradient (matching hierarchy page)
    if (item.Is_Bogus) {
        return {
            background: '#f44336',
            border: '#d32f2f',
            highlight: {
                background: '#e53935',
                border: '#c62828'
            }
        };
    }
    
    // Contaminated nodes - orange gradient (matching hierarchy page)
    if (item.Is_Contaminated) {
        return {
            background: '#ff9800',
            border: '#f57c00',
            highlight: {
                background: '#fb8c00',
                border: '#ef6c00'
            }
        };
    }
    
    // Check if node data is missing (no file available)
    if (!item.Entity_Name || item.Entity_Name === item.PAN) {
        return {
            background: '#9e9e9e',
            border: '#757575',
            highlight: {
                background: '#757575',
                border: '#616161'
            }
        };
    }
    
    // OK nodes - green gradient (matching hierarchy page)
    return {
        background: '#4caf50',
        border: '#388e3c',
        highlight: {
            background: '#43a047',
            border: '#2e7d32'
        }
    };
}

function getNodeSize(item) {
    // Root node is always largest
    if (item.PAN === ROOT_NODE_PAN) return 35;
    
    const purchases = item.Total_Purchases || 0;
    
    // Size based on purchase volume
    if (purchases > 500000000) return 30;      // >50Cr
    if (purchases > 100000000) return 25;      // >10Cr
    if (purchases > 50000000) return 22;       // >5Cr
    if (purchases > 10000000) return 20;       // >1Cr
    if (purchases > 1000000) return 18;        // >10L
    return 15;                                 // Default
}

function getNodeStatus(item) {
    if (item.Is_Bogus) return 'BOGUS';
    if (item.Is_Contaminated) return 'CONTAMINATED';
    if (!item.Entity_Name || item.Entity_Name === item.PAN) return 'MISSING';
    return 'OK';
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

function showCustomTooltip(nodeId, event) {
    const node = allNodes.get(nodeId);
    if (!node || !node.data) return;
    
    const tooltip = document.querySelector('.custom-tooltip');
    if (!tooltip) return;
    
    // Create tooltip content
    tooltip.innerHTML = createNodeTooltip(node.data);
    
    // Position tooltip
    const rect = document.getElementById('mynetwork').getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    tooltip.style.left = (x + 15) + 'px';
    tooltip.style.top = (y - 10) + 'px';
    tooltip.style.display = 'block';
    tooltip.style.opacity = '1';
    
    // Adjust position if tooltip goes off screen
    setTimeout(() => {
        const tooltipRect = tooltip.getBoundingClientRect();
        const containerRect = document.getElementById('mynetwork').getBoundingClientRect();
        
        if (tooltipRect.right > containerRect.right) {
            tooltip.style.left = (x - tooltipRect.width - 15) + 'px';
        }
        
        if (tooltipRect.bottom > containerRect.bottom) {
            tooltip.style.top = (y - tooltipRect.height + 10) + 'px';
        }
    }, 10);
}

function hideCustomTooltip() {
    const tooltip = document.querySelector('.custom-tooltip');
    if (tooltip) {
        tooltip.style.opacity = '0';
        setTimeout(() => {
            tooltip.style.display = 'none';
        }, 200);
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
