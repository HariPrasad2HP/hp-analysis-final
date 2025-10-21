#!/usr/bin/env python3
"""
Health Check Script for GST Analysis System

This script verifies that all components of the GST Analysis System are working correctly.
"""

import sys
import os
import json
import urllib.request
from pathlib import Path

# Add project paths
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, project_root)

def check_files():
    """Check if required data files exist"""
    print("📁 Checking Data Files...")
    
    required_files = [
        'data/output/gst_table_data.json',
        'data/output/pan_names.json', 
        'data/output/pan_availability.json',
        'data/output/gst_analysis_results.xlsx',
        'data/output/gst_analysis_report.txt'
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"  ✅ {file_path} ({size:,} bytes)")
        else:
            print(f"  ❌ {file_path} (missing)")
            all_exist = False
    
    return all_exist

def check_web_server(base_url="http://localhost:8001"):
    """Check if web server is running and responding"""
    print(f"🌐 Checking Web Server ({base_url})...")
    
    # Test pages
    pages = {
        'Hierarchy': '/',
        'DAG': '/dag',
        'Health': '/health'
    }
    
    page_results = {}
    for name, path in pages.items():
        try:
            with urllib.request.urlopen(f"{base_url}{path}", timeout=5) as response:
                status = response.status
                content_length = len(response.read())
                page_results[name] = (status, content_length)
                print(f"  ✅ {name}: {status} ({content_length:,} chars)")
        except Exception as e:
            page_results[name] = (0, str(e))
            print(f"  ❌ {name}: {e}")
    
    return page_results

def check_api_endpoints(base_url="http://localhost:8001"):
    """Check API endpoints"""
    print("🔌 Checking API Endpoints...")
    
    endpoints = {
        'Config': '/api/config',
        'Summary': '/api/analysis/summary', 
        'High Risk': '/api/analysis/high-risk',
        'GST Data': '/api/data/gst_table_data.json',
        'PAN Names': '/api/data/pan_names.json',
        'PAN Availability': '/api/data/pan_availability.json'
    }
    
    api_results = {}
    for name, path in endpoints.items():
        try:
            with urllib.request.urlopen(f"{base_url}{path}", timeout=5) as response:
                data = json.loads(response.read().decode())
                if isinstance(data, list):
                    result = f"{len(data)} items"
                elif isinstance(data, dict):
                    result = f"{len(data)} keys"
                else:
                    result = f"{type(data).__name__}"
                
                api_results[name] = (200, result)
                print(f"  ✅ {name}: {result}")
        except Exception as e:
            api_results[name] = (0, str(e))
            print(f"  ❌ {name}: {e}")
    
    return api_results

def check_analysis_script():
    """Check if analysis script can run"""
    print("⚙️  Checking Analysis Script...")
    
    try:
        # Test help command
        import subprocess
        result = subprocess.run([
            sys.executable, 'scripts/run_analysis.py', '--help'
        ], cwd=project_root, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("  ✅ Analysis script help works")
            return True
        else:
            print(f"  ❌ Analysis script error: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Analysis script check failed: {e}")
        return False

def main():
    """Run all health checks"""
    print("🏥 GST Analysis System Health Check")
    print("=" * 50)
    
    results = {
        'files': check_files(),
        'web_server': check_web_server(),
        'api_endpoints': check_api_endpoints(), 
        'analysis_script': check_analysis_script()
    }
    
    print("\n📊 Health Check Summary")
    print("=" * 50)
    
    # Files check
    if results['files']:
        print("✅ Data Files: All required files present")
    else:
        print("❌ Data Files: Some files missing - run analysis with --export-json")
    
    # Web server check
    web_pages = results['web_server']
    working_pages = sum(1 for status, _ in web_pages.values() if status == 200)
    total_pages = len(web_pages)
    if working_pages == total_pages:
        print(f"✅ Web Server: All {total_pages} pages working")
    else:
        print(f"❌ Web Server: {working_pages}/{total_pages} pages working")
    
    # API endpoints check
    api_endpoints = results['api_endpoints']
    working_apis = sum(1 for status, _ in api_endpoints.values() if status == 200)
    total_apis = len(api_endpoints)
    if working_apis == total_apis:
        print(f"✅ API Endpoints: All {total_apis} endpoints working")
    else:
        print(f"❌ API Endpoints: {working_apis}/{total_apis} endpoints working")
    
    # Analysis script check
    if results['analysis_script']:
        print("✅ Analysis Script: Ready to run")
    else:
        print("❌ Analysis Script: Issues detected")
    
    # Overall status
    all_good = (
        results['files'] and 
        working_pages == total_pages and 
        working_apis == total_apis and 
        results['analysis_script']
    )
    
    print("\n🎯 Overall Status")
    print("=" * 50)
    if all_good:
        print("✅ GST Analysis System is fully operational!")
        print("\n🚀 Ready to use:")
        print("   • Run analysis: python3 scripts/run_analysis.py")
        print("   • Web interface: http://localhost:8001")
        print("   • Health check: python3 scripts/health_check.py")
        return 0
    else:
        print("❌ GST Analysis System has issues that need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
