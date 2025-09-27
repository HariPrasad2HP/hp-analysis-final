#!/usr/bin/env python3
"""
Enhanced Hierarchical GST Data Analyzer

This enhanced version includes configuration management, improved error handling,
and additional analysis features.

Author: GST Analysis Team
Date: 2025-09-20
"""

import pandas as pd
import os
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging
from datetime import datetime

from utils.logger import setup_logger

logger = logging.getLogger(__name__)

@dataclass
class TransactionRecord:
    """Represents a single transaction record"""
    pan: str
    transaction_type: str  # 'GSTR1-R' for sales, 'GSTR1-P' for purchases
    amount: float
    party_name: str
    taxpayer_type: str
    business_nature: str = ""
    turnover_range: str = ""
    income_range: str = ""

@dataclass
class NodeData:
    """Represents aggregated data for a node"""
    pan: str
    total_sales: float = 0.0
    total_purchases: float = 0.0
    purchase_to_sales_ratio: float = 0.0
    is_bogus: bool = False
    children: Set[str] = None
    parents: Set[str] = None
    transaction_count: int = 0
    avg_transaction_size: float = 0.0
    risk_score: float = 0.0
    
    def __post_init__(self):
        if self.children is None:
            self.children = set()
        if self.parents is None:
            self.parents = set()

@dataclass
class AnalysisMetrics:
    """Analysis performance and quality metrics"""
    total_nodes: int = 0
    bogus_nodes: int = 0
    processing_time: float = 0.0
    files_processed: int = 0
    errors_encountered: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

class EnhancedAnalyzer:
    """
    Enhanced GST analyzer with configuration management and advanced features
    """
    
    def __init__(self, config):
        """
        Initialize the enhanced analyzer
        
        Args:
            config: Configuration object with settings
        """
        self.config = config
        self.cache: Dict[str, NodeData] = {}
        self.file_mapping: Dict[str, str] = {}
        self.pan_names: Dict[str, str] = {}
        self.processing_stack: Set[str] = set()
        self.metrics = AnalysisMetrics()
        
        # Setup logging
        setup_logger(config.get('log_level', 'INFO'))
        
        # Build file mapping and PAN names
        self._build_file_mapping()
        self._build_pan_names_mapping()
    
    def _build_file_mapping(self):
        """Build mapping of PAN to Excel file names"""
        try:
            data_dir = self.config.get('data_directory', 'data/input')
            excel_files = [f for f in os.listdir(data_dir) 
                          if f.endswith('.xlsx') and not f.startswith('~')]
            
            for file in excel_files:
                # Extract PAN from filename (first part before underscore)
                pan = file.split('_')[0]
                self.file_mapping[pan] = file
            
            logger.info(f"Built file mapping for {len(self.file_mapping)} files")
        except Exception as e:
            logger.error(f"Error building file mapping: {e}")
            if not self.config.get('continue_on_file_error', True):
                raise
    
    def _build_pan_names_mapping(self):
        """Build mapping of PAN to Entity Names from Excel files"""
        try:
            data_dir = self.config.get('data_directory', 'data/input')
            
            for pan, filename in self.file_mapping.items():
                file_path = os.path.join(data_dir, filename)
                try:
                    df = pd.read_excel(file_path, header=None)
                    # Read entity name from row 6, column C (0-indexed: row 5, column 2)
                    if df.shape[0] > 5 and df.shape[1] > 2:
                        entity_name = df.iloc[5, 2]
                        if pd.notna(entity_name) and str(entity_name).strip():
                            self.pan_names[pan] = str(entity_name).strip()
                        else:
                            self.pan_names[pan] = pan  # Fallback to PAN
                    else:
                        self.pan_names[pan] = pan  # Fallback to PAN
                except Exception as e:
                    logger.warning(f"Could not read entity name from {filename}: {e}")
                    self.pan_names[pan] = pan  # Fallback to PAN
            
            logger.info(f"Built PAN names mapping for {len(self.pan_names)} entities")
        except Exception as e:
            logger.error(f"Error building PAN names mapping: {e}")
    
    def get_entity_name(self, pan: str) -> str:
        """Get entity name for a PAN, with fallback to PAN if not found"""
        return self.pan_names.get(pan, pan)
    
    def _read_excel_data(self, file_path: str) -> List[TransactionRecord]:
        """
        Read transaction data from Excel file
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of TransactionRecord objects
        """
        try:
            df = pd.read_excel(file_path, header=None)
            
            # Get data starting from configured row (default: 19)
            data_start_row = self.config.get('data_start_row', 19)
            data_start_idx = data_start_row - 1  # Convert to 0-indexed
            data_rows = df.iloc[data_start_idx:]
            
            # Find where data ends (first empty row)
            end_idx = None
            for i, row in data_rows.iterrows():
                pan_col = self.config.get('column_mapping', {}).get('pan', 2)  # Column C
                if pd.isna(row.iloc[pan_col]) or row.iloc[pan_col] == '':
                    if i > data_start_idx:  # Skip header row
                        end_idx = i
                        break
            
            if end_idx:
                actual_data = df.iloc[data_start_idx + 1:end_idx]  # Skip header
            else:
                actual_data = df.iloc[data_start_idx + 1:]  # Skip header
            
            records = []
            for _, row in actual_data.iterrows():
                try:
                    # Extract data using column mapping
                    col_map = self.config.get('column_mapping', {})
                    pan_col = col_map.get('pan', 2)
                    info_col = col_map.get('info_code', 1)
                    amount_col = col_map.get('amount', 3)
                    name_col = col_map.get('party_name', 4)
                    type_col = col_map.get('taxpayer_type', 5)
                    business_col = col_map.get('business_nature', 6)
                    turnover_col = col_map.get('turnover_range', 7)
                    income_col = col_map.get('income_range', 8)
                    
                    if pd.isna(row.iloc[pan_col]) or pd.isna(row.iloc[info_col]) or pd.isna(row.iloc[amount_col]):
                        continue
                    
                    # Convert amount to float, handling string values
                    amount_val = row.iloc[amount_col]
                    if pd.isna(amount_val):
                        amount = 0.0
                    else:
                        try:
                            amount = float(str(amount_val).replace(',', ''))
                        except (ValueError, TypeError):
                            amount = 0.0
                    
                    record = TransactionRecord(
                        pan=str(row.iloc[pan_col]).strip(),
                        transaction_type=str(row.iloc[info_col]).strip(),
                        amount=amount,
                        party_name=str(row.iloc[name_col]) if not pd.isna(row.iloc[name_col]) else "",
                        taxpayer_type=str(row.iloc[type_col]) if not pd.isna(row.iloc[type_col]) else "",
                        business_nature=str(row.iloc[business_col]) if not pd.isna(row.iloc[business_col]) else "",
                        turnover_range=str(row.iloc[turnover_col]) if not pd.isna(row.iloc[turnover_col]) else "",
                        income_range=str(row.iloc[income_col]) if not pd.isna(row.iloc[income_col]) else ""
                    )
                    records.append(record)
                except (ValueError, IndexError) as e:
                    if self.config.get('skip_invalid_rows', True):
                        logger.warning(f"Skipping invalid row in {file_path}: {e}")
                        self.metrics.errors_encountered += 1
                        continue
                    else:
                        raise
            
            self.metrics.files_processed += 1
            logger.debug(f"Read {len(records)} records from {file_path}")
            return records
            
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            self.metrics.errors_encountered += 1
            if not self.config.get('continue_on_file_error', True):
                raise
            return []
    
    def _calculate_node_aggregates(self, records: List[TransactionRecord]) -> Tuple[float, float, int]:
        """
        Calculate total sales, purchases, and transaction count
        
        Args:
            records: List of transaction records
            
        Returns:
            Tuple of (total_sales, total_purchases, transaction_count)
        """
        total_sales = 0.0
        total_purchases = 0.0
        transaction_count = 0
        
        for record in records:
            if record.transaction_type == 'GSTR1-R':  # Sales
                total_sales += record.amount
                transaction_count += 1
            elif record.transaction_type == 'GSTR1-P':  # Purchases
                total_purchases += record.amount
                transaction_count += 1
        
        return total_sales, total_purchases, transaction_count
    
    def _calculate_risk_score(self, node_data: NodeData) -> float:
        """
        Calculate risk score based on multiple factors
        
        Args:
            node_data: NodeData object
            
        Returns:
            Risk score (0-100)
        """
        risk_score = 0.0
        
        # Factor 1: Purchase/Sales ratio
        if node_data.total_sales > 0:
            ratio = node_data.purchase_to_sales_ratio
            if ratio < 0.1:
                risk_score += 40  # Very low purchases
            elif ratio < 0.3:
                risk_score += 30
            elif ratio < 0.5:
                risk_score += 20
        else:
            if node_data.total_purchases > 0:
                risk_score += 50  # Purchases without sales
        
        # Factor 2: Transaction volume (in crores)
        total_volume = node_data.total_sales + node_data.total_purchases
        if total_volume > 1e9:  # > 100 crores
            risk_score += 15
        elif total_volume > 1e8:  # > 10 crores
            risk_score += 10
        
        # Factor 3: Number of children (complexity)
        if len(node_data.children) > 10:
            risk_score += 10
        elif len(node_data.children) > 5:
            risk_score += 5
        
        # Factor 4: Average transaction size (in crores)
        if node_data.avg_transaction_size > 1e8:  # > 10 crores per transaction
            risk_score += 10
        
        return min(risk_score, 100.0)  # Cap at 100
    
    def _process_node(self, pan: str, root_records: List[TransactionRecord] = None, visited: Set[str] = None) -> NodeData:
        """
        Process a single node and its children recursively
        
        Args:
            pan: PAN of the node to process
            root_records: Records from root file for this PAN
            visited: Set of already visited nodes to prevent infinite recursion
            
        Returns:
            NodeData object with aggregated information
        """
        if visited is None:
            visited = set()
        
        # Check cache first
        if pan in self.cache:
            self.metrics.cache_hits += 1
            return self.cache[pan]
        
        self.metrics.cache_misses += 1
        
        # Prevent circular dependencies
        if pan in visited:
            logger.warning(f"Circular dependency detected for PAN: {pan}")
            return NodeData(pan=pan)
        
        visited.add(pan)
        
        # Initialize node data
        node_data = NodeData(pan=pan)
        
        # First, add any transactions from root file for this PAN
        if root_records:
            pan_root_records = [r for r in root_records if r.pan == pan]
            if pan_root_records:
                root_sales, root_purchases, root_count = self._calculate_node_aggregates(pan_root_records)
                node_data.total_sales += root_sales
                node_data.total_purchases += root_purchases
                node_data.transaction_count += root_count
        
        # Check if this PAN has a corresponding Excel file
        if pan in self.file_mapping:
            data_dir = self.config.get('data_directory', 'data/input')
            file_path = os.path.join(data_dir, self.file_mapping[pan])
            records = self._read_excel_data(file_path)
            
            # Calculate direct sales and purchases for this node from its own file
            direct_sales, direct_purchases, direct_count = self._calculate_node_aggregates(records)
            node_data.total_sales += direct_sales
            node_data.total_purchases += direct_purchases
            node_data.transaction_count += direct_count
            
            # Process children (only PANs with purchase transactions - GSTR1-P)
            # Exclude root node from being a child of any other node
            root_node_pan = self.config.get('root_node_pan', 'AAYCA4390A')
            purchase_child_pans = set()
            for record in records:
                if (record.pan != pan and 
                    record.pan not in visited and 
                    record.pan != root_node_pan and  # Don't add root node as child
                    record.transaction_type == 'GSTR1-P'):  # Only purchase transactions
                    purchase_child_pans.add(record.pan)
            
            # Add only purchase PANs as children
            for child_pan in purchase_child_pans:
                node_data.children.add(child_pan)
                
                # If child has its own file, recursively process it to build the hierarchy
                # but DO NOT aggregate child data into parent - each node should have its own data
                if child_pan in self.file_mapping:
                    child_data = self._process_node(child_pan, None, visited.copy())
                    child_data.parents.add(pan)
                    # Note: We don't aggregate child data into parent anymore
                    # Each node contains only its own sales/purchases
        
        # Calculate derived metrics
        if node_data.total_sales > 0:
            node_data.purchase_to_sales_ratio = node_data.total_purchases / node_data.total_sales
        else:
            node_data.purchase_to_sales_ratio = float('inf') if node_data.total_purchases > 0 else 0.0
        
        # Enhanced bogus detection
        bogus_threshold = self.config.get('bogus_threshold', 0.5)
        node_data.is_bogus = (
            node_data.purchase_to_sales_ratio == 0.0 or
            node_data.purchase_to_sales_ratio < bogus_threshold or
            node_data.purchase_to_sales_ratio > 2.0 or
            node_data.purchase_to_sales_ratio == float('inf')
        )
        
        if node_data.transaction_count > 0:
            total_amount = node_data.total_sales + node_data.total_purchases
            node_data.avg_transaction_size = total_amount / node_data.transaction_count
        
        node_data.risk_score = self._calculate_risk_score(node_data)
        
        # Cache the result
        max_cache_size = self.config.get('max_cache_size', 10000)
        if len(self.cache) < max_cache_size:
            self.cache[pan] = node_data
        
        visited.remove(pan)
        return node_data
    
    def analyze_hierarchy(self) -> Dict[str, NodeData]:
        """
        Analyze the complete hierarchy starting from the root file
        
        Returns:
            Dictionary mapping PAN to NodeData
        """
        start_time = datetime.now()
        logger.info("Starting enhanced hierarchical analysis...")
        
        # Read root file
        data_dir = self.config.get('data_directory', 'data/input')
        root_file = self.config.get('root_file', 'gst_analysis_results.xlsx')
        root_file_path = os.path.join(data_dir, root_file)
        
        # Extract root PAN from filename (first part before underscore)
        root_node_pan = root_file.split('_')[0]
        logger.info(f"Root node PAN extracted from filename: {root_node_pan}")
        
        root_records = self._read_excel_data(root_file_path)
        
        if not root_records:
            logger.error("No records found in root file")
            return {}
        
        # Start hierarchical processing from the root node
        # This will recursively process all children based on purchase relationships
        logger.info(f"Starting hierarchical analysis from root node: {root_node_pan}")
        
        try:
            root_node_data = self._process_node(root_node_pan, root_records)
            
            # Collect all processed nodes from cache (includes root and all descendants)
            results = dict(self.cache)
            
            # Update metrics
            self.metrics.total_nodes = len(results)
            self.metrics.bogus_nodes = sum(1 for node in results.values() if node.is_bogus)
            
            logger.info(f"Processed {len(results)} nodes in hierarchy starting from {root_node_pan}")
            logger.info(f"Root node - Sales: {root_node_data.total_sales:.2f}, "
                       f"Purchases: {root_node_data.total_purchases:.2f}, "
                       f"Children: {len(root_node_data.children)}")
            
        except Exception as e:
            logger.error(f"Error processing root node {root_node_pan}: {e}")
            self.metrics.errors_encountered += 1
            if not self.config.get('continue_on_file_error', True):
                raise
            results = {}
        
        end_time = datetime.now()
        self.metrics.processing_time = (end_time - start_time).total_seconds()

        logger.info(f"Analysis complete. Processed {len(results)} total nodes in {self.metrics.processing_time:.2f} seconds.")
        return results
    
    def generate_report(self, results: Dict[str, NodeData]) -> str:
        """
        Generate a comprehensive report
        
        Args:
            results: Dictionary of analysis results
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 100)
        report.append("ENHANCED HIERARCHICAL GST ANALYSIS REPORT")
        report.append("=" * 100)
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Configuration: Bogus Threshold = {self.config.get('bogus_threshold', 0.5)}")
        report.append("")
        
        # Performance metrics
        report.append("PERFORMANCE METRICS:")
        report.append(f"Processing Time: {self.metrics.processing_time:.2f} seconds")
        report.append(f"Files Processed: {self.metrics.files_processed}")
        report.append(f"Cache Hits: {self.metrics.cache_hits}")
        report.append(f"Cache Misses: {self.metrics.cache_misses}")
        report.append(f"Errors Encountered: {self.metrics.errors_encountered}")
        report.append("")
        
        # Summary statistics
        total_nodes = len(results)
        bogus_nodes = sum(1 for node in results.values() if node.is_bogus)
        total_sales = sum(node.total_sales for node in results.values())
        total_purchases = sum(node.total_purchases for node in results.values())
        high_risk_nodes = sum(1 for node in results.values() if node.risk_score > 70)
        
        report.append("SUMMARY STATISTICS:")
        report.append(f"Total Nodes Analyzed: {total_nodes}")
        report.append(f"Bogus Nodes Detected: {bogus_nodes} ({bogus_nodes/total_nodes*100:.1f}%)")
        report.append(f"High Risk Nodes (Score > 70): {high_risk_nodes} ({high_risk_nodes/total_nodes*100:.1f}%)")
        report.append(f"Total Sales Amount: ₹{total_sales:,.2f}")
        report.append(f"Total Purchases Amount: ₹{total_purchases:,.2f}")
        report.append(f"Overall P/S Ratio: {total_purchases/total_sales:.4f}" if total_sales > 0 else "Overall P/S Ratio: N/A")
        report.append("")
        
        # Risk analysis
        risk_distribution = defaultdict(int)
        for node in results.values():
            if node.risk_score >= 80:
                risk_distribution['Very High'] += 1
            elif node.risk_score >= 60:
                risk_distribution['High'] += 1
            elif node.risk_score >= 40:
                risk_distribution['Medium'] += 1
            elif node.risk_score >= 20:
                risk_distribution['Low'] += 1
            else:
                risk_distribution['Very Low'] += 1
        
        report.append("RISK DISTRIBUTION:")
        for risk_level, count in risk_distribution.items():
            percentage = count / total_nodes * 100
            report.append(f"{risk_level}: {count} ({percentage:.1f}%)")
        report.append("")
        
        # Detailed node analysis
        report.append("DETAILED ANALYSIS:")
        report.append("-" * 100)
        report.append(f"{'PAN':<15} {'Sales':<15} {'Purchases':<15} {'P/S Ratio':<10} {'Risk':<6} {'Status':<8} {'Children'}")
        report.append("-" * 100)
        
        # Sort by risk score (highest first)
        sorted_results = sorted(results.items(), key=lambda x: x[1].risk_score, reverse=True)
        
        for pan, node in sorted_results:
            status = "BOGUS" if node.is_bogus else "OK"
            children_count = len(node.children)
            ratio_str = f"{node.purchase_to_sales_ratio:.4f}" if node.purchase_to_sales_ratio != float('inf') else "∞"
            
            report.append(f"{pan:<15} {node.total_sales:<15,.0f} {node.total_purchases:<15,.0f} "
                         f"{ratio_str:<10} {node.risk_score:<6.1f} {status:<8} {children_count}")
        
        return "\n".join(report)
    
    def export_results(self, results: Dict[str, NodeData], output_file: str):
        """
        Export analysis results to Excel file
        
        Args:
            results: Dictionary of analysis results
            output_file: Path to output Excel file
        """
        try:
            # Prepare data for export
            export_data = []
            for pan, node in results.items():
                export_data.append({
                    'PAN': pan,
                    'Total_Sales': node.total_sales,
                    'Total_Purchases': node.total_purchases,
                    'Purchase_to_Sales_Ratio': node.purchase_to_sales_ratio,
                    'Risk_Score': node.risk_score,
                    'Is_Bogus': node.is_bogus,
                    'Transaction_Count': node.transaction_count,
                    'Avg_Transaction_Size': node.avg_transaction_size,
                    'Children_Count': len(node.children),
                    'Parents_Count': len(node.parents),
                    'Children_PANs': ', '.join(node.children) if node.children else '',
                    'Parents_PANs': ', '.join(node.parents) if node.parents else ''
                })
            
            df = pd.DataFrame(export_data)
            
            # Create Excel writer with multiple sheets
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Main results sheet
                df.to_excel(writer, sheet_name='Analysis_Results', index=False)
                
                # Summary sheet
                summary_data = {
                    'Metric': [
                        'Total Nodes',
                        'Bogus Nodes',
                        'Bogus Percentage',
                        'Total Sales',
                        'Total Purchases',
                        'Overall P/S Ratio',
                        'Processing Time (seconds)',
                        'Files Processed',
                        'Errors Encountered'
                    ],
                    'Value': [
                        len(results),
                        self.metrics.bogus_nodes,
                        f"{self.metrics.bogus_nodes/len(results)*100:.1f}%",
                        sum(node.total_sales for node in results.values()),
                        sum(node.total_purchases for node in results.values()),
                        sum(node.total_purchases for node in results.values()) / sum(node.total_sales for node in results.values()) if sum(node.total_sales for node in results.values()) > 0 else 'N/A',
                        self.metrics.processing_time,
                        self.metrics.files_processed,
                        self.metrics.errors_encountered
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Bogus nodes sheet
                bogus_data = [asdict(node) for pan, node in results.items() if node.is_bogus]
                if bogus_data:
                    bogus_df = pd.DataFrame(bogus_data)
                    bogus_df.to_excel(writer, sheet_name='Bogus_Nodes', index=False)
            
            logger.info(f"Results exported to {output_file}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
