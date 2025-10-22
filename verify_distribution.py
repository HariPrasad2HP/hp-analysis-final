#!/usr/bin/env python3
"""
GST Analysis System - Distribution Verification Script
Verifies that all distribution files are present and valid
"""

import os
import sys
import zipfile
import tarfile
from pathlib import Path

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[0;34m",
        "SUCCESS": "\033[0;32m", 
        "WARNING": "\033[1;33m",
        "ERROR": "\033[0;31m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}[{status}]{colors['RESET']} {message}")

def check_file_exists(file_path, description):
    """Check if a file exists and print status"""
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print_status(f"✅ {description}: {file_path} ({size:,} bytes)", "SUCCESS")
        return True
    else:
        print_status(f"❌ {description}: {file_path} (missing)", "ERROR")
        return False

def verify_zip_package(zip_path):
    """Verify ZIP package integrity"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Test the ZIP file
            bad_file = zipf.testzip()
            if bad_file:
                print_status(f"❌ ZIP package corrupted: {bad_file}", "ERROR")
                return False
            
            # Check for key files
            files = zipf.namelist()
            required_files = [
                'gst-analysis-system-v1.0.0/README.md',
                'gst-analysis-system-v1.0.0/install.bat',
                'gst-analysis-system-v1.0.0/requirements.txt',
                'gst-analysis-system-v1.0.0/setup.py'
            ]
            
            missing_files = []
            for req_file in required_files:
                if not any(f.endswith(req_file.split('/')[-1]) for f in files):
                    missing_files.append(req_file.split('/')[-1])
            
            if missing_files:
                print_status(f"❌ ZIP missing files: {', '.join(missing_files)}", "ERROR")
                return False
            
            print_status(f"✅ ZIP package valid ({len(files)} files)", "SUCCESS")
            return True
            
    except Exception as e:
        print_status(f"❌ ZIP verification failed: {e}", "ERROR")
        return False

def verify_tarball(tar_path):
    """Verify TAR.GZ package integrity"""
    try:
        with tarfile.open(tar_path, 'r:gz') as tarf:
            # Get file list
            files = tarf.getnames()
            
            # Check for key files
            required_files = ['README.md', 'install.sh', 'requirements.txt', 'setup.py']
            missing_files = []
            
            for req_file in required_files:
                if not any(f.endswith(req_file) for f in files):
                    missing_files.append(req_file)
            
            if missing_files:
                print_status(f"❌ TAR.GZ missing files: {', '.join(missing_files)}", "ERROR")
                return False
            
            print_status(f"✅ TAR.GZ package valid ({len(files)} files)", "SUCCESS")
            return True
            
    except Exception as e:
        print_status(f"❌ TAR.GZ verification failed: {e}", "ERROR")
        return False

def main():
    """Main verification function"""
    print_status("GST Analysis System - Distribution Verification", "INFO")
    print("=" * 60)
    
    all_good = True
    
    # Check core distribution files
    print_status("Checking core files...", "INFO")
    core_files = [
        ("README.md", "Main documentation"),
        ("requirements.txt", "Python dependencies"),
        ("setup.py", "Package setup script"),
        ("LICENSE", "License file"),
        ("install.sh", "Linux/macOS installer"),
        ("install.bat", "Windows installer"),
        ("Dockerfile", "Docker configuration"),
        ("docker-compose.yml", "Docker Compose file"),
        ("create_distribution.py", "Distribution creator"),
        ("DISTRIBUTION_GUIDE.md", "User guide"),
        ("DEPLOYMENT_CHECKLIST.md", "Deployment checklist")
    ]
    
    for file_path, description in core_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    # Check configuration files
    print_status("\nChecking configuration files...", "INFO")
    config_files = [
        ("config/settings.yaml", "Default configuration"),
        ("config/settings.example.yaml", "Example configuration")
    ]
    
    for file_path, description in config_files:
        if not check_file_exists(file_path, description):
            all_good = False
    
    # Check distribution packages
    print_status("\nChecking distribution packages...", "INFO")
    dist_dir = Path("dist")
    
    if not dist_dir.exists():
        print_status("❌ Distribution directory missing", "ERROR")
        all_good = False
    else:
        # Check package files
        zip_file = dist_dir / "gst-analysis-system-v1.0.0.zip"
        tar_file = dist_dir / "gst-analysis-system-v1.0.0.tar.gz"
        wheel_file = dist_dir / "gst_analysis_system-1.0.0-py3-none-any.whl"
        info_file = dist_dir / "DISTRIBUTION_INFO.txt"
        
        package_files = [
            (zip_file, "Windows ZIP package"),
            (tar_file, "Linux/macOS TAR.GZ package"),
            (wheel_file, "Python wheel package"),
            (info_file, "Distribution info file")
        ]
        
        for file_path, description in package_files:
            if not check_file_exists(file_path, description):
                all_good = False
        
        # Verify package integrity
        if zip_file.exists():
            print_status("\nVerifying ZIP package integrity...", "INFO")
            if not verify_zip_package(zip_file):
                all_good = False
        
        if tar_file.exists():
            print_status("\nVerifying TAR.GZ package integrity...", "INFO")
            if not verify_tarball(tar_file):
                all_good = False
    
    # Check executable permissions
    print_status("\nChecking executable permissions...", "INFO")
    executable_files = ["install.sh", "create_distribution.py"]
    
    for exe_file in executable_files:
        if os.path.exists(exe_file):
            if os.access(exe_file, os.X_OK):
                print_status(f"✅ {exe_file} is executable", "SUCCESS")
            else:
                print_status(f"⚠️  {exe_file} not executable (run: chmod +x {exe_file})", "WARNING")
        
    # Final summary
    print("\n" + "=" * 60)
    if all_good:
        print_status("🎉 All verification checks passed!", "SUCCESS")
        print_status("📦 Distribution is ready for deployment!", "SUCCESS")
        
        # Show package sizes
        if dist_dir.exists():
            print_status("\n📊 Package sizes:", "INFO")
            for file in dist_dir.iterdir():
                if file.is_file() and file.suffix in ['.zip', '.gz', '.whl']:
                    size_mb = file.stat().st_size / (1024 * 1024)
                    print(f"   - {file.name}: {size_mb:.1f} MB")
        
        return 0
    else:
        print_status("❌ Some verification checks failed!", "ERROR")
        print_status("Please fix the issues above before distribution.", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(main())
