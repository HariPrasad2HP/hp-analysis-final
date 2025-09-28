#!/usr/bin/env python3
"""
Main Analysis Script

User-friendly utility for running different GST analysis scenarios.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
import warnings

# Add src directory and project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, project_root)

# Suppress specific openpyxl warning about default style
# Example warning:
# /.../openpyxl/styles/stylesheet.py:237: UserWarning: Workbook contains no default style, apply openpyxl's default
#   warn("Workbook contains no default style, apply openpyxl's default")
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module=r"openpyxl\.styles\.stylesheet",
    message=r"Workbook contains no default style, apply openpyxl's default"
)

from analyzers.enhanced_analyzer import EnhancedAnalyzer
from utils.logger import setup_logger
from config.config import ConfigManager, get_config_for_environment

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description='GST Hierarchical Data Analysis System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis.py                    # Run with default settings
  python run_analysis.py --env production  # Use production environment
  python run_analysis.py --config custom.yaml --threshold 0.3
  python run_analysis.py --data-dir /path/to/excel/files
        """
    )
    
    parser.add_argument('--config', type=str, 
                       help='Path to configuration file')
    parser.add_argument('--env', type=str, default='default',
                       choices=['default', 'development', 'production', 'testing'],
                       help='Environment configuration to use')
    parser.add_argument('--data-dir', type=str,
                       help='Directory containing Excel files')
    parser.add_argument('--output-dir', type=str,
                       help='Output directory for results')
    parser.add_argument('--threshold', type=float,
                       help='Bogus detection threshold (0-1)')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--no-cache', action='store_true',
                       help='Disable caching')
    parser.add_argument('--export-json', action='store_true', default=True,
                       help='Export results to JSON for web interface (default: True)')
    parser.add_argument('--no-json', action='store_true',
                       help='Disable JSON export')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress console output')
    
    args = parser.parse_args()
    
    try:
        # Setup logging
        if not args.quiet:
            setup_logger(args.log_level)
        
        logger = logging.getLogger(__name__)
        
        # Load configuration
        if args.config:
            config_manager = ConfigManager(args.config)
        else:
            config_manager = ConfigManager()
            if args.env != 'default':
                config_manager.config = get_config_for_environment(args.env)
        
        config = config_manager.get_config()
        
        # Apply command line overrides
        if args.data_dir:
            config.data_directory = args.data_dir
        if args.output_dir:
            config.output_directory = args.output_dir
        if args.threshold:
            config.bogus_threshold = args.threshold
        if args.no_cache:
            config.enable_caching = False
        if args.log_level:
            config.log_level = args.log_level
        
        # Validate configuration
        if not config_manager.validate_config():
            logger.error("Configuration validation failed")
            return 1
        
        if not args.quiet:
            logger.info("Starting GST Analysis System")
            logger.info(f"Data Directory: {config.data_directory}")
            logger.info(f"Output Directory: {config.output_directory}")
            logger.info(f"Bogus Threshold: {config.bogus_threshold}")
            logger.info(f"Environment: {args.env}")
        
        # Initialize analyzer
        analyzer = EnhancedAnalyzer(config.__dict__)
        
        # Run analysis
        results = analyzer.analyze_hierarchy()
        
        if not results:
            logger.error("Analysis returned no results")
            return 1
        
        # Generate and save report
        report = analyzer.generate_report(results)
        
        if not args.quiet:
            print("\n" + "="*80)
            print(report)
            print("="*80)
        
        # Export results to Excel
        output_file = os.path.join(config.output_directory, config.excel_filename)
        analyzer.export_results(results, output_file)
        
        # Save text report
        report_file = os.path.join(config.output_directory, config.report_filename)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Export JSON for web interface (default enabled, unless --no-json specified)
        if args.export_json and not args.no_json:
            import json
            
            # Prepare data for web interface
            web_data = []
            for pan, node in results.items():
                web_data.append({
                    'PAN': pan,
                    'Entity_Name': analyzer.get_entity_name(pan),
                    'Total_Sales': float(node.total_sales),
                    'Total_Purchases': float(node.total_purchases),
                    'Original_Total_Purchases': float(node.original_total_purchases),
                    'Adjusted_Purchases': float(node.adjusted_purchases),
                    'Purchase_to_Sales_Ratio': float(node.purchase_to_sales_ratio) if node.purchase_to_sales_ratio != float('inf') else None,
                    'Is_Bogus': bool(node.is_bogus),
                    'Bogus_Value': float(node.bogus_value),
                    'Is_Contaminated': bool(node.is_contaminated),
                    'Contamination_Level': float(node.contamination_level),
                    'Transaction_Count': int(node.transaction_count),
                    'Avg_Transaction_Size': float(node.avg_transaction_size),
                    'Children_PANs': ', '.join(node.children) if node.children else '',
                    'Parents_PANs': ', '.join(node.parents) if node.parents else ''
                })
            
            json_file = os.path.join(config.output_directory, config.json_filename)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(web_data, f, indent=2, ensure_ascii=False)
            
            # Generate additional data files for web interface
            # PAN names mapping (PAN -> Entity Name)
            pan_names = {item['PAN']: analyzer.get_entity_name(item['PAN']) for item in web_data}
            pan_names_file = os.path.join(config.output_directory, 'pan_names.json')
            with open(pan_names_file, 'w', encoding='utf-8') as f:
                json.dump(pan_names, f, indent=2, ensure_ascii=False)
            
            # PAN availability (all PANs in our data are considered available)
            pan_availability = {item['PAN']: True for item in web_data}
            pan_availability_file = os.path.join(config.output_directory, 'pan_availability.json')
            with open(pan_availability_file, 'w', encoding='utf-8') as f:
                json.dump(pan_availability, f, indent=2, ensure_ascii=False)
            
            if not args.quiet:
                logger.info(f"JSON data exported to: {json_file}")
                logger.info(f"PAN names exported to: {pan_names_file}")
                logger.info(f"PAN availability exported to: {pan_availability_file}")
        
        if not args.quiet:
            logger.info(f"Analysis complete!")
            logger.info(f"Report saved to: {report_file}")
            logger.info(f"Excel results saved to: {output_file}")
            logger.info(f"Processed {len(results)} nodes")
            logger.info(f"Found {sum(1 for n in results.values() if n.is_bogus)} bogus transactions")
        
        return 0
        
    except KeyboardInterrupt:
        if not args.quiet:
            print("\nAnalysis interrupted by user")
        return 130
    except Exception as e:
        if not args.quiet:
            logger.error(f"Analysis failed: {e}")
            if args.log_level == 'DEBUG':
                import traceback
                traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
