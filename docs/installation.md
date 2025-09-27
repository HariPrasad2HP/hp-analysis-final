# Installation Guide

This guide will help you install and set up the GST Analysis System on your machine.

## Prerequisites

### System Requirements
- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended for large datasets)
- **Storage**: At least 2GB free space for the application and data

### Required Software
- Python 3.8+ with pip
- Git (for cloning the repository)
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Installation Methods

### Method 1: Quick Installation (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/gst-analysis-system.git
   cd gst-analysis-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the package**
   ```bash
   pip install -e .
   ```

5. **Verify installation**
   ```bash
   python scripts/run_analysis.py --help
   ```

### Method 2: Development Installation

For developers who want to contribute to the project:

1. **Clone and setup**
   ```bash
   git clone https://github.com/your-org/gst-analysis-system.git
   cd gst-analysis-system
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

3. **Setup pre-commit hooks** (optional)
   ```bash
   pre-commit install
   ```

### Method 3: Docker Installation (Coming Soon)

Docker support will be added in future releases.

## Configuration

### 1. Create Configuration File

Copy the sample configuration:
```bash
cp config/settings.yaml config/local.yaml
```

Edit `config/local.yaml` to match your environment:
```yaml
data_directory: "/path/to/your/excel/files"
output_directory: "/path/to/output/directory"
log_level: "INFO"
web_port: 8000
```

### 2. Environment Variables (Optional)

You can also use environment variables:
```bash
export GST_DATA_DIR="/path/to/excel/files"
export GST_OUTPUT_DIR="/path/to/output"
export GST_LOG_LEVEL="INFO"
```

### 3. Data Directory Setup

Create the required directories:
```bash
mkdir -p data/input data/output data/cache logs
```

Place your Excel files in the `data/input` directory.

## Verification

### Test the Installation

1. **Run analysis help**
   ```bash
   python scripts/run_analysis.py --help
   ```

2. **Start web server**
   ```bash
   python scripts/start_server.py --help
   ```

3. **Run tests** (if development installation)
   ```bash
   python -m pytest tests/
   ```

### Sample Data Test

If you have sample data, run a quick analysis:
```bash
python scripts/run_analysis.py --env development --export-json
```

## Troubleshooting

### Common Issues

#### 1. Python Version Error
```
ERROR: Python 3.8+ is required
```
**Solution**: Install Python 3.8 or higher from [python.org](https://python.org)

#### 2. Permission Denied
```
PermissionError: [Errno 13] Permission denied
```
**Solution**: 
- On Windows: Run as Administrator
- On macOS/Linux: Use `sudo` or check file permissions

#### 3. Module Not Found
```
ModuleNotFoundError: No module named 'pandas'
```
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Excel File Reading Error
```
Error reading Excel file: No such file or directory
```
**Solution**: 
- Check file paths in configuration
- Ensure Excel files are in the correct directory
- Verify file permissions

#### 5. Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution**: Use a different port
```bash
python scripts/start_server.py --port 8080
```

### Getting Help

1. **Check logs**: Look in the `logs/` directory for detailed error messages
2. **Enable debug mode**: Use `--log-level DEBUG` for verbose output
3. **Validate configuration**: Run with `--env testing` to check setup
4. **Check system resources**: Ensure sufficient memory and disk space

## Next Steps

After successful installation:

1. **Read the [Usage Guide](usage.md)** to learn how to use the system
2. **Review the [Configuration Reference](configuration.md)** for advanced settings
3. **Check out [Examples](examples/)** for common use cases

## Updating

To update to the latest version:

```bash
git pull origin main
pip install -r requirements.txt
pip install -e .
```

## Uninstallation

To remove the GST Analysis System:

```bash
pip uninstall gst-analysis-system
# Remove the project directory
rm -rf gst-analysis-system
```

---

**Need help?** Open an issue on GitHub or contact the development team.
