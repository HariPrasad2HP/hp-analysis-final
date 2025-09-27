#!/usr/bin/env python3
"""
Check Root Nodes Script

Analyzes the current data to find actual root nodes and provides information
about what's available vs what's configured.
"""

import sys
import os
import json

# Add src directory and project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, project_root)

def check_root_nodes():
    """Check what root nodes are available in the current data"""
    
    # Load current data
    data_file = os.path.join(project_root, 'data', 'output', 'gst_table_data.json')
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("   Run the analysis first to generate data.")
        return
    
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        print(f"✅ Loaded {len(data)} records from data file")
        print()
        
        # Find nodes with no parents (root nodes)
        root_nodes = []
        for node in data:
            parents = node.get('Parents_PANs', '')
            if not parents or parents.strip() == '':
                root_nodes.append(node)
        
        print(f"🔍 Found {len(root_nodes)} root nodes (nodes with no parents):")
        print("-" * 80)
        
        for i, node in enumerate(root_nodes[:10], 1):  # Show first 10
            pan = node.get('PAN', 'Unknown')
            entity_name = node.get('Entity_Name', pan)
            sales = node.get('Total_Sales', 0)
            purchases = node.get('Total_Purchases', 0)
            children = node.get('Children_PANs', '')
            child_count = len(children.split(',')) if children.strip() else 0
            
            print(f"{i:2d}. PAN: {pan}")
            print(f"    Entity: {entity_name}")
            print(f"    Sales: ₹{sales:,.0f}")
            print(f"    Purchases: ₹{purchases:,.0f}")
            print(f"    Children: {child_count}")
            print()
        
        if len(root_nodes) > 10:
            print(f"... and {len(root_nodes) - 10} more root nodes")
            print()
        
        # Check if configured root node exists
        from config.config import ConfigManager
        config_manager = ConfigManager()
        config = config_manager.get_config()
        configured_root = config.root_node_pan
        
        print(f"🎯 Configured root node: {configured_root}")
        
        configured_node = next((node for node in data if node.get('PAN') == configured_root), None)
        if configured_node:
            print(f"✅ Configured root node found in data!")
            parents = configured_node.get('Parents_PANs', '')
            if parents and parents.strip():
                print(f"⚠️  WARNING: Configured root node has parents: {parents}")
                print("   This means it's not actually a root node in the current data.")
            else:
                print("✅ Configured root node is indeed a root node (no parents)")
        else:
            print(f"❌ Configured root node NOT found in data!")
            print("   The analysis needs to be run with the correct root file.")
            
            # Check if root file exists
            root_file_path = os.path.join(config.data_directory, config.root_file)
            if os.path.exists(root_file_path):
                print(f"✅ Root file exists: {config.root_file}")
                print("   Run the analysis to include this root node in the data.")
            else:
                print(f"❌ Root file not found: {config.root_file}")
                print("   Check the configuration and ensure the root file exists.")
        
        print()
        print("💡 Recommendations:")
        if configured_node:
            print("   - The web interface should work correctly")
            print("   - If you're still seeing errors, clear browser cache")
        else:
            print("   - Run the analysis script to generate data with the configured root node")
            print("   - Or update settings.yaml to use one of the available root nodes")
            if root_nodes:
                print(f"   - Available root nodes: {', '.join([n['PAN'] for n in root_nodes[:5]])}")
        
    except Exception as e:
        print(f"❌ Error reading data file: {e}")

if __name__ == "__main__":
    check_root_nodes()
