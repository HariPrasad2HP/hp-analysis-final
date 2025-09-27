#!/usr/bin/env python3
"""
Configuration Management

Handles configuration loading, validation, and environment-specific settings
for the GST Analysis System.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class AnalysisConfig:
    """Configuration for GST analysis"""
    
    # Data directories
    data_directory: str = "../ai"
    output_directory: str = "data/output"
    cache_directory: str = "data/cache"
    
    # File settings
    root_file: str = ""
    data_start_row: int = 19
    
    # Column mapping (0-indexed)
    column_mapping: Dict[str, int] = None
    
    # Analysis parameters
    bogus_threshold: float = 0.5
    risk_threshold: float = 70.0
    
    # Processing settings
    enable_caching: bool = True
    max_cache_size: int = 10000
    continue_on_file_error: bool = True
    skip_invalid_rows: bool = True
    
    # Output settings
    excel_filename: str = "gst_analysis_results.xlsx"
    report_filename: str = "gst_analysis_report.txt"
    json_filename: str = "gst_table_data.json"
    
    # Logging settings
    log_level: str = "INFO"
    log_to_file: bool = True
    log_filename: str = "gst_analysis.log"
    
    # Web interface settings
    web_host: str = "localhost"
    web_port: int = 8000
    web_debug: bool = False
    
    # Root node configuration
    root_node_pan: str = ""
    
    # Risk scoring weights
    risk_factors: Dict[str, float] = None
    
    # Currency formatting
    currency: Dict[str, any] = None
    
    def __post_init__(self):
        if self.column_mapping is None:
            self.column_mapping = {
                'info_code': 1,      # Column B - Information Code
                'pan': 3,            # Column D - Party PAN
                'amount': 7,         # Column H - Aggregated Transaction Value
                'party_name': 4,     # Column E - Party Name
                'taxpayer_type': 5,  # Column F - Taxpayer Type
                'business_nature': 9, # Column J - Nature of Business
                'turnover_range': 10, # Column K - Turnover range
                'income_range': 11   # Column L - Income range
            }
        
        if self.risk_factors is None:
            self.risk_factors = {
                'purchase_sales_ratio': 0.4,
                'transaction_volume': 0.3,
                'file_availability': 0.2,
                'children_complexity': 0.1
            }
        
        if self.currency is None:
            self.currency = {
                'format': 'indian',
                'precision': 2,
                'show_currency_symbol': True
            }

class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/settings.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> AnalysisConfig:
        """Load configuration from file or use defaults"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                logger.info(f"Loaded configuration from {self.config_file}")
                return AnalysisConfig(**config_data)
            else:
                logger.warning(f"Configuration file {self.config_file} not found, using defaults")
                return AnalysisConfig()
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration")
            return AnalysisConfig()
    
    def get_config(self) -> AnalysisConfig:
        """Get the current configuration"""
        return self.config
    
    def update_config(self, **kwargs):
        """Update configuration with new values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                logger.warning(f"Unknown configuration key: {key}")
    
    def save_config(self, file_path: Optional[str] = None):
        """Save current configuration to file"""
        save_path = file_path or self.config_file
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            config_dict = asdict(self.config)
            
            with open(save_path, 'w') as f:
                if save_path.endswith('.yaml') or save_path.endswith('.yml'):
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_dict, f, indent=2)
            
            logger.info(f"Configuration saved to {save_path}")
        
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def validate_config(self) -> bool:
        """Validate the current configuration"""
        try:
            # Check required directories
            for dir_attr in ['data_directory', 'output_directory', 'cache_directory']:
                dir_path = getattr(self.config, dir_attr)
                if not os.path.exists(dir_path):
                    logger.warning(f"Directory does not exist: {dir_path}")
                    # Create directory if it doesn't exist
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info(f"Created directory: {dir_path}")
            
            # Check root file exists
            root_file_path = os.path.join(self.config.data_directory, self.config.root_file)
            if not os.path.exists(root_file_path):
                logger.error(f"Root file not found: {root_file_path}")
                return False
            
            # Validate thresholds
            if not 0 <= self.config.bogus_threshold <= 1:
                logger.error(f"Invalid bogus_threshold: {self.config.bogus_threshold}")
                return False
            
            if not 0 <= self.config.risk_threshold <= 100:
                logger.error(f"Invalid risk_threshold: {self.config.risk_threshold}")
                return False
            
            # Validate column mapping
            required_columns = ['pan', 'info_code', 'amount']
            for col in required_columns:
                if col not in self.config.column_mapping:
                    logger.error(f"Missing required column mapping: {col}")
                    return False
            
            logger.info("Configuration validation passed")
            return True
        
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False

def load_config_from_file(file_path: str) -> AnalysisConfig:
    """Load configuration from a specific file"""
    manager = ConfigManager(file_path)
    return manager.get_config()

def get_default_config() -> AnalysisConfig:
    """Get default configuration"""
    return AnalysisConfig()

def get_config_for_environment(env: str) -> AnalysisConfig:
    """Get configuration for a specific environment"""
    env_configs = {
        'development': {
            'log_level': 'DEBUG',
            'web_debug': True,
            'enable_caching': True,
            'continue_on_file_error': True
        },
        'production': {
            'log_level': 'INFO',
            'web_debug': False,
            'enable_caching': True,
            'continue_on_file_error': False
        },
        'testing': {
            'log_level': 'WARNING',
            'web_debug': False,
            'enable_caching': False,
            'continue_on_file_error': True,
            'data_directory': 'tests/test_data',
            'output_directory': 'tests/output'
        }
    }
    
    base_config = AnalysisConfig()
    
    if env in env_configs:
        for key, value in env_configs[env].items():
            setattr(base_config, key, value)
        logger.info(f"Loaded {env} environment configuration")
    else:
        logger.warning(f"Unknown environment: {env}, using default configuration")
    
    return base_config

def create_sample_config(file_path: str = "config/settings.yaml"):
    """Create a sample configuration file"""
    config = AnalysisConfig()
    manager = ConfigManager()
    manager.config = config
    manager.save_config(file_path)
    logger.info(f"Sample configuration created at {file_path}")

# Environment variable overrides
def apply_env_overrides(config: AnalysisConfig) -> AnalysisConfig:
    """Apply environment variable overrides to configuration"""
    
    env_mappings = {
        'GST_DATA_DIR': 'data_directory',
        'GST_OUTPUT_DIR': 'output_directory',
        'GST_CACHE_DIR': 'cache_directory',
        'GST_ROOT_FILE': 'root_file',
        'GST_BOGUS_THRESHOLD': 'bogus_threshold',
        'GST_LOG_LEVEL': 'log_level',
        'GST_WEB_HOST': 'web_host',
        'GST_WEB_PORT': 'web_port',
        'GST_WEB_DEBUG': 'web_debug'
    }
    
    for env_var, config_attr in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Convert types as needed
            if config_attr in ['bogus_threshold']:
                env_value = float(env_value)
            elif config_attr in ['web_port']:
                env_value = int(env_value)
            elif config_attr in ['web_debug']:
                env_value = env_value.lower() in ('true', '1', 'yes', 'on')
            
            setattr(config, config_attr, env_value)
            logger.info(f"Applied environment override: {config_attr} = {env_value}")
    
    return config
