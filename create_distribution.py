#!/usr/bin/env python3
"""
GST Analysis System - Distribution Package Creator
Creates a distributable package for end users
"""

import os
import shutil
import zipfile
import tarfile
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def print_status(message):
    print(f"[INFO] {message}")

def print_success(message):
    print(f"[SUCCESS] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def create_distribution():
    """Create distribution packages"""
    
    print_status("Creating GST Analysis System distribution packages...")
    
    # Get version from setup.py
    version = "1.0.0"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Distribution directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Package name
    package_name = f"gst-analysis-system-v{version}"
    
    # Files and directories to include
    include_items = [
        "src/",
        "scripts/",
        "config/",
        "docs/",
        "requirements.txt",
        "setup.py",
        "README.md",
        "install.sh",
        "install.bat",
        "Dockerfile",
        "docker-compose.yml",
        "LICENSE" if os.path.exists("LICENSE") else None,
    ]
    
    # Filter out None items
    include_items = [item for item in include_items if item and os.path.exists(item)]
    
    # Exclude patterns
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".git",
        ".gitignore",
        "venv/",
        "env/",
        ".env",
        "data/",
        "logs/",
        "reports/",
        "dist/",
        "build/",
        "*.egg-info",
        ".pytest_cache",
        ".coverage",
        "node_modules/",
    ]
    
    def should_exclude(path):
        """Check if a path should be excluded"""
        path_str = str(path)
        for pattern in exclude_patterns:
            if pattern in path_str or path_str.endswith(pattern.replace("*", "")):
                return True
        return False
    
    # Create temporary directory for packaging
    temp_dir = Path(f"temp_{package_name}")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    temp_dir.mkdir()
    package_dir = temp_dir / package_name
    package_dir.mkdir()
    
    print_status("Copying files...")
    
    # Copy files and directories
    for item in include_items:
        src_path = Path(item)
        if src_path.is_file():
            shutil.copy2(src_path, package_dir)
            print_status(f"Copied file: {item}")
        elif src_path.is_dir():
            dest_path = package_dir / src_path.name
            shutil.copytree(src_path, dest_path, ignore=lambda dir, files: [
                f for f in files if should_exclude(Path(dir) / f)
            ])
            print_status(f"Copied directory: {item}")
    
    # Create sample data directory structure
    sample_data_dir = package_dir / "data"
    sample_data_dir.mkdir()
    (sample_data_dir / "input").mkdir()
    (sample_data_dir / "output").mkdir()
    
    # Create sample configuration if it doesn't exist
    config_dir = package_dir / "config"
    if not (config_dir / "settings.yaml").exists():
        if (config_dir / "settings.example.yaml").exists():
            shutil.copy2(config_dir / "settings.example.yaml", config_dir / "settings.yaml")
    
    # Create README for data directory
    with open(sample_data_dir / "README.md", "w") as f:
        f.write("""# Data Directory

## Structure

- `input/`: Place your GST data files here
  - `gst_table_data.xlsx`: Main GST transaction data
  - `sales_records.xlsx`: Sales transaction records
  - `entity_master.xlsx`: Entity master data (optional)

- `output/`: Generated analysis results will be saved here
  - `gst_table_data.json`: Processed GST data
  - `hierarchy_data.json`: Hierarchy analysis results
  - `reports/`: Generated reports

## Data Format

Please refer to the main README.md for detailed data format requirements.
""")
    
    # Create installation guide
    with open(package_dir / "INSTALL.md", "w") as f:
        f.write("""# Installation Guide

## Quick Start

### Windows Users
1. Extract the package
2. Double-click `install.bat`
3. Follow the on-screen instructions

### Linux/macOS Users
1. Extract the package
2. Open terminal in the extracted directory
3. Run: `chmod +x install.sh && ./install.sh`

### Docker Users
1. Extract the package
2. Run: `docker-compose up -d`

## Manual Installation

See README.md for detailed manual installation instructions.

## Next Steps

After installation:
1. Place your data files in `data/input/`
2. Configure settings in `config/settings.yaml`
3. Run analysis: `gst-analyze`
4. Start web server: `gst-server`
5. Open http://localhost:8000 in your browser

## Support

- Check README.md for troubleshooting
- Run health check: `python scripts/health_check.py`
""")
    
    print_status("Creating distribution packages...")
    
    # Create ZIP package (for Windows users)
    zip_path = dist_dir / f"{package_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                arc_path = file_path.relative_to(temp_dir)
                zipf.write(file_path, arc_path)
    
    print_success(f"Created ZIP package: {zip_path}")
    
    # Create TAR.GZ package (for Linux/macOS users)
    tar_path = dist_dir / f"{package_name}.tar.gz"
    with tarfile.open(tar_path, 'w:gz') as tarf:
        tarf.add(temp_dir, arcname=".")
    
    print_success(f"Created TAR.GZ package: {tar_path}")
    
    # Create Python wheel (for pip installation)
    print_status("Creating Python wheel...")
    try:
        subprocess.run([sys.executable, "setup.py", "bdist_wheel"], 
                      cwd=package_dir, check=True, capture_output=True)
        
        # Move wheel to dist directory
        wheel_dir = package_dir / "dist"
        if wheel_dir.exists():
            for wheel_file in wheel_dir.glob("*.whl"):
                shutil.move(wheel_file, dist_dir)
                print_success(f"Created wheel: {dist_dir / wheel_file.name}")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create wheel: {e}")
    
    # Clean up temporary directory
    shutil.rmtree(temp_dir)
    
    # Create distribution info file
    info_file = dist_dir / "DISTRIBUTION_INFO.txt"
    with open(info_file, "w") as f:
        f.write(f"""GST Analysis System - Distribution Packages
=============================================

Version: {version}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Packages:
- {package_name}.zip (Windows users)
- {package_name}.tar.gz (Linux/macOS users)
- Python wheel files (for pip installation)

Installation:
1. Extract the appropriate package for your system
2. Follow the instructions in INSTALL.md
3. Or use the automated installation scripts

Requirements:
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended)
- 1GB free disk space

Support:
- See README.md for detailed documentation
- Run health_check.py to verify installation
""")
    
    print_success("Distribution packages created successfully!")
    print_status(f"Packages available in: {dist_dir.absolute()}")
    
    # List created files
    print_status("Created files:")
    for file in dist_dir.iterdir():
        if file.is_file():
            size = file.stat().st_size / (1024 * 1024)  # MB
            print(f"  - {file.name} ({size:.1f} MB)")

def main():
    """Main function"""
    if not Path("setup.py").exists():
        print_error("setup.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    create_distribution()

if __name__ == "__main__":
    main()
