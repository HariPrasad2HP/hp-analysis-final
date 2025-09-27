# Usage Guide

This guide covers how to use the GST Analysis System for analyzing hierarchical GST transaction data.

## Quick Start

### 1. Prepare Your Data

Place your Excel files in the `data/input` directory:
```
data/input/
├── gst_analysis_results.xlsx  # Root file
├── AAYCA4390A_company1.xlsx   # Individual PAN files
├── AQPPJ0006Q_company2.xlsx
└── ...
```

### 2. Run Analysis

```bash
# Basic analysis
python scripts/run_analysis.py

# With custom settings
python scripts/run_analysis.py --env production --threshold 0.3
```

### 3. View Results

```bash
# Start web interface
python scripts/start_server.py

# Open browser to http://localhost:8000
```

## Command Line Interface

### Analysis Command

```bash
python scripts/run_analysis.py [OPTIONS]
```

#### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--config FILE` | Configuration file path | `--config custom.yaml` |
| `--env ENV` | Environment (default, development, production, testing) | `--env production` |
| `--data-dir DIR` | Input data directory | `--data-dir /path/to/excel/files` |
| `--output-dir DIR` | Output directory | `--output-dir /path/to/output` |
| `--threshold FLOAT` | Bogus detection threshold (0-1) | `--threshold 0.3` |
| `--log-level LEVEL` | Logging level | `--log-level DEBUG` |
| `--no-cache` | Disable caching | `--no-cache` |
| `--export-json` | Export JSON for web interface | `--export-json` |
| `--quiet` | Suppress console output | `--quiet` |

#### Examples

```bash
# Development analysis with debug logging
python scripts/run_analysis.py --env development --log-level DEBUG

# Production analysis with custom threshold
python scripts/run_analysis.py --env production --threshold 0.4 --export-json

# Analysis with custom directories
python scripts/run_analysis.py --data-dir /custom/data --output-dir /custom/output

# Quiet analysis for automation
python scripts/run_analysis.py --quiet --export-json
```

### Web Server Command

```bash
python scripts/start_server.py [OPTIONS]
```

#### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--config FILE` | Configuration file path | `--config custom.yaml` |
| `--env ENV` | Environment | `--env development` |
| `--host HOST` | Host to bind to | `--host 0.0.0.0` |
| `--port PORT` | Port to bind to | `--port 8080` |
| `--debug` | Enable debug mode | `--debug` |
| `--no-reload` | Disable auto-reload | `--no-reload` |
| `--log-level LEVEL` | Logging level | `--log-level DEBUG` |

#### Examples

```bash
# Development server with debug mode
python scripts/start_server.py --env development --debug

# Production server on custom port
python scripts/start_server.py --env production --port 8080

# Server accessible from network
python scripts/start_server.py --host 0.0.0.0 --port 8000
```

## Web Interface

### Dashboard

The dashboard provides an overview of your GST analysis:

- **Summary Cards**: Total nodes, bogus transactions, sales, purchases
- **Charts**: Risk distribution, transaction status, purchase vs sales
- **Tables**: High-risk entities, recent results

### Hierarchy View

Interactive tree view of the purchase hierarchy:

- **Root Node**: AAYCA4390A with 16 direct children
- **Expandable Nodes**: Click [+] to expand children
- **Filters**: Filter by purchase value, sales value, status
- **Indian Currency**: Values displayed in crores/lakhs

#### Using Filters

1. **Purchase Value Filter**: Show only nodes with purchases above threshold
2. **Sales Value Filter**: Show only nodes with sales above threshold  
3. **Status Filter**: Filter by OK, Bogus, or Missing File status

### DAG Visualization

Interactive network graph of the hierarchy:

- **Node Types**: Different colors for root, OK, bogus, missing, high-purchase
- **Interactive**: Click to expand/collapse, drag to pan, scroll to zoom
- **Controls**: Fit to view, expand all, collapse all
- **Statistics**: Real-time node and edge counts

## Configuration

### Configuration File

Create a custom configuration file:

```yaml
# config/custom.yaml
data_directory: "/path/to/excel/files"
output_directory: "/path/to/output"
bogus_threshold: 0.4
risk_threshold: 75.0
web_port: 8080
log_level: "DEBUG"
```

Use with:
```bash
python scripts/run_analysis.py --config config/custom.yaml
```

### Environment Configurations

#### Development
- Debug logging enabled
- Caching enabled
- Continue on file errors
- Web debug mode

#### Production  
- Info logging
- Caching enabled
- Stop on file errors
- Web debug disabled

#### Testing
- Warning logging only
- Caching disabled
- Continue on file errors
- Test data directories

## Data Format

### Excel File Structure

#### Root File (gst_analysis_results.xlsx)
- **Row 19+**: Data starts from row 19
- **Column B**: Transaction type (GSTR1-R/GSTR1-P)
- **Column C**: PAN number
- **Column D**: Amount
- **Column E**: Party name
- **Columns F-I**: Additional metadata

#### Individual PAN Files
- **Filename**: `{PAN}_{description}.xlsx`
- **Same structure** as root file
- **Contains transactions** for that specific PAN

### Expected Data Quality

- **PAN Format**: 10-character alphanumeric
- **Amounts**: Numeric values (strings with commas accepted)
- **Transaction Types**: 'GSTR1-R' for sales, 'GSTR1-P' for purchases
- **File Availability**: Not all PANs need corresponding files

## Analysis Results

### Output Files

After analysis, you'll find these files in the output directory:

#### 1. Excel Report (`gst_analysis_results.xlsx`)
- **Analysis_Results**: Main results with all metrics
- **Summary**: High-level statistics
- **Bogus_Nodes**: Filtered bogus transactions

#### 2. Text Report (`gst_analysis_report.txt`)
- Performance metrics
- Summary statistics  
- Risk distribution
- Detailed node analysis

#### 3. JSON Data (`gst_table_data.json`)
- Web interface data
- API-friendly format
- All analysis results

#### 4. Supporting Files
- `pan_names.json`: PAN to company name mapping
- `pan_availability.json`: List of available PAN files
- `gst_analysis.log`: Detailed logs

### Understanding Results

#### Risk Scores (0-100)
- **0-20**: Very Low Risk
- **20-40**: Low Risk  
- **40-60**: Medium Risk
- **60-80**: High Risk
- **80-100**: Very High Risk

#### Transaction Status
- **OK**: Normal transaction (P/S ratio 0.5-2.0)
- **BOGUS**: Suspicious transaction (P/S ratio <0.5 or >2.0)
- **MISSING FILE**: PAN referenced but no Excel file found

#### Purchase/Sales Ratio
- **< 0.5**: Very low purchases (potential bogus)
- **0.5-1.5**: Normal range
- **> 1.5**: High purchases (potential bogus)
- **∞**: Purchases without sales

## Troubleshooting

### Common Issues

#### 1. No Results
- Check if Excel files are in correct directory
- Verify root file exists and has correct name
- Check file permissions

#### 2. Incorrect Values
- Verify Excel data starts from row 19
- Check column mapping in configuration
- Ensure amounts are numeric

#### 3. Web Interface Not Loading
- Check if analysis was run with `--export-json`
- Verify JSON files exist in output directory
- Check web server logs

#### 4. Performance Issues
- Enable caching for large datasets
- Increase memory allocation
- Use production environment for better performance

### Debug Mode

Enable debug logging for detailed information:
```bash
python scripts/run_analysis.py --log-level DEBUG
```

Check logs in the `logs/` directory for detailed error messages.

## Best Practices

### 1. Data Preparation
- Ensure consistent Excel file format
- Use meaningful filenames with PAN prefixes
- Validate data quality before analysis

### 2. Configuration
- Use environment-specific configurations
- Set appropriate thresholds for your use case
- Enable caching for repeated analysis

### 3. Performance
- Run analysis during off-peak hours for large datasets
- Monitor memory usage
- Use SSD storage for better I/O performance

### 4. Security
- Keep sensitive data in secure directories
- Use appropriate file permissions
- Don't expose web interface to public networks in production

## Integration

### API Usage

The web interface provides REST APIs:

```bash
# Get analysis summary
curl http://localhost:8000/api/analysis/summary

# Get high-risk entities  
curl http://localhost:8000/api/analysis/high-risk

# Search entities
curl "http://localhost:8000/api/analysis/search?q=AAYCA"
```

### Automation

Integrate with cron jobs or task schedulers:

```bash
# Daily analysis
0 2 * * * /path/to/venv/bin/python /path/to/scripts/run_analysis.py --quiet --export-json
```

---

**Next**: Check out the [API Documentation](api.md) for programmatic access.
