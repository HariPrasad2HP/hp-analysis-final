#!/usr/bin/env python3
"""
Data Loader Utility

Handles loading and preprocessing of GST data from various sources.
"""

import os
import json
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class DataLoader:
    """Handles loading GST data from various sources"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data loader
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.data_directory = config.get('data_directory', 'data/input')
        self.output_directory = config.get('output_directory', 'data/output')
        
    def load_analysis_results(self) -> Optional[List[Dict]]:
        """
        Load analysis results from JSON file
        
        Returns:
            List of analysis result dictionaries or None if not found
        """
        try:
            json_file = os.path.join(self.output_directory, 'gst_table_data.json')
            
            if not os.path.exists(json_file):
                logger.warning(f"Analysis results file not found: {json_file}")
                return None
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded {len(data)} analysis results from {json_file}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading analysis results: {e}")
            return None
    
    def load_pan_names(self) -> Dict[str, str]:
        """
        Load PAN to company name mapping
        
        Returns:
            Dictionary mapping PAN to company names
        """
        try:
            names_file = os.path.join(self.output_directory, 'pan_names.json')
            
            if not os.path.exists(names_file):
                logger.warning(f"PAN names file not found: {names_file}")
                return {}
            
            with open(names_file, 'r', encoding='utf-8') as f:
                names = json.load(f)
            
            logger.info(f"Loaded {len(names)} PAN names from {names_file}")
            return names
            
        except Exception as e:
            logger.error(f"Error loading PAN names: {e}")
            return {}
    
    def load_pan_availability(self) -> List[str]:
        """
        Load list of available PAN files
        
        Returns:
            List of available PAN IDs
        """
        try:
            availability_file = os.path.join(self.output_directory, 'pan_availability.json')
            
            if not os.path.exists(availability_file):
                logger.warning(f"PAN availability file not found: {availability_file}")
                return []
            
            with open(availability_file, 'r', encoding='utf-8') as f:
                availability = json.load(f)
            
            logger.info(f"Loaded {len(availability)} available PANs from {availability_file}")
            return availability
            
        except Exception as e:
            logger.error(f"Error loading PAN availability: {e}")
            return []
    
    def get_excel_files(self) -> List[str]:
        """
        Get list of Excel files in data directory
        
        Returns:
            List of Excel file paths
        """
        try:
            if not os.path.exists(self.data_directory):
                logger.error(f"Data directory not found: {self.data_directory}")
                return []
            
            excel_files = []
            for file in os.listdir(self.data_directory):
                if file.endswith(('.xlsx', '.xls')) and not file.startswith('~'):
                    excel_files.append(os.path.join(self.data_directory, file))
            
            logger.info(f"Found {len(excel_files)} Excel files in {self.data_directory}")
            return excel_files
            
        except Exception as e:
            logger.error(f"Error getting Excel files: {e}")
            return []
    
    def load_excel_file(self, file_path: str, sheet_name: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Load Excel file into DataFrame
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name to load (default: first sheet)
            
        Returns:
            DataFrame or None if loading failed
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Excel file not found: {file_path}")
                return None
            
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            logger.debug(f"Loaded Excel file: {file_path} ({df.shape[0]} rows, {df.shape[1]} columns)")
            return df
            
        except Exception as e:
            logger.error(f"Error loading Excel file {file_path}: {e}")
            return None
    
    def extract_pan_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract PAN from filename
        
        Args:
            filename: Excel filename
            
        Returns:
            PAN string or None if extraction failed
        """
        try:
            # Remove path and extension
            basename = os.path.basename(filename)
            name_without_ext = os.path.splitext(basename)[0]
            
            # Extract PAN (first part before underscore)
            pan = name_without_ext.split('_')[0]
            
            # Validate PAN format (10 characters, alphanumeric)
            if len(pan) == 10 and pan.isalnum():
                return pan.upper()
            else:
                logger.warning(f"Invalid PAN format extracted from {filename}: {pan}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting PAN from filename {filename}: {e}")
            return None
    
    def build_file_mapping(self) -> Dict[str, str]:
        """
        Build mapping of PAN to Excel file names
        
        Returns:
            Dictionary mapping PAN to filename
        """
        try:
            excel_files = self.get_excel_files()
            file_mapping = {}
            
            for file_path in excel_files:
                filename = os.path.basename(file_path)
                pan = self.extract_pan_from_filename(filename)
                
                if pan:
                    file_mapping[pan] = filename
            
            logger.info(f"Built file mapping for {len(file_mapping)} PANs")
            return file_mapping
            
        except Exception as e:
            logger.error(f"Error building file mapping: {e}")
            return {}
    
    def save_json_data(self, data: Any, filename: str) -> bool:
        """
        Save data to JSON file
        
        Args:
            data: Data to save
            filename: Output filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(self.output_directory, exist_ok=True)
            
            file_path = os.path.join(self.output_directory, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Saved JSON data to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving JSON data to {filename}: {e}")
            return False
    
    def load_json_data(self, filename: str) -> Optional[Any]:
        """
        Load data from JSON file
        
        Args:
            filename: JSON filename
            
        Returns:
            Loaded data or None if failed
        """
        try:
            file_path = os.path.join(self.output_directory, filename)
            
            if not os.path.exists(file_path):
                logger.warning(f"JSON file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded JSON data from {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading JSON data from {filename}: {e}")
            return None
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get summary of available data
        
        Returns:
            Dictionary with data summary information
        """
        try:
            summary = {
                'excel_files_count': len(self.get_excel_files()),
                'analysis_results_available': os.path.exists(os.path.join(self.output_directory, 'gst_table_data.json')),
                'pan_names_available': os.path.exists(os.path.join(self.output_directory, 'pan_names.json')),
                'pan_availability_available': os.path.exists(os.path.join(self.output_directory, 'pan_availability.json')),
                'data_directory': self.data_directory,
                'output_directory': self.output_directory
            }
            
            # Get analysis results count if available
            if summary['analysis_results_available']:
                results = self.load_analysis_results()
                summary['analysis_results_count'] = len(results) if results else 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting data summary: {e}")
            return {}
