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
from typing import Dict, List, Tuple, Optional, Set, Any
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
    original_total_purchases: float = 0.0  # Store original before contamination adjustment
    purchase_to_sales_ratio: float = 0.0
    transaction_count: int = 0
    avg_transaction_size: float = 0.0
    is_bogus: bool = False
    bogus_value: float = 0.0  # Sum of purchases from bogus children
    is_contaminated: bool = False  # True if all/majority children are bogus
    contamination_level: float = 0.0  # Percentage of bogus children
    adjusted_purchases: float = 0.0  # Purchases after removing bogus amounts
    children: Set[str] = None
    parents: Set[str] = None
    
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
    
    def get_sales_records(self, pan: str) -> List[Dict[str, Any]]:
        """
        Get all sales records for a specific PAN
        
        Args:
            pan: PAN to get sales records for
            
        Returns:
            List of sales record dictionaries
        """
        if pan not in self.file_mapping:
            return []
        
        try:
            data_dir = self.config.get('data_directory', 'data/input')
            file_path = os.path.join(data_dir, self.file_mapping[pan])
            records = self._read_excel_data(file_path)
            
            # Filter for sales records only (GSTR1-R)
            sales_records = []
            for record in records:
                if record.transaction_type == 'GSTR1-R':
                    sales_records.append({
                        'buyer_pan': record.pan,
                        'buyer_name': record.party_name or record.pan,
                        'amount': float(record.amount),
                        'transaction_type': record.transaction_type,
                        'taxpayer_type': record.taxpayer_type or '',
                        'business_nature': record.business_nature or '',
                        'turnover_range': record.turnover_range or '',
                        'income_range': record.income_range or ''
                    })
            
            return sales_records
            
        except Exception as e:
            logger.error(f"Error reading sales records for {pan}: {e}")
            return []
    
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
    
    
    def _calculate_bogus_values(self, results: Dict[str, NodeData]) -> None:
        """
        Calculate bogus values and perform contamination analysis for all nodes.
        
{{ ... }}
        Args:
            results: Dictionary of all processed nodes
        """
        logger.info("Calculating bogus values and contamination analysis...")
        
        # For each node, find the actual purchase amounts paid to bogus children
        for pan, node_data in results.items():
            bogus_value = 0.0
            bogus_purchase_amounts = {}  # Track individual bogus child purchase amounts
            
            # Store original total purchases before any adjustments
            node_data.original_total_purchases = node_data.total_purchases
            
            # Read the node's own file to get transaction details
            if pan in self.file_mapping:
                data_dir = self.config.get('data_directory', 'data/input')
                file_path = os.path.join(data_dir, self.file_mapping[pan])
                
                try:
                    records = self._read_excel_data(file_path)
                    
                    # Check each transaction record
                    for record in records:
                        # If this record is a purchase (GSTR1-P) from a bogus child
                        if (record.transaction_type == 'GSTR1-P' and 
                            record.pan in node_data.children and
                            record.pan in results and
                            results[record.pan].is_bogus):
                            
                            # Add the actual purchase amount paid to this bogus child
                            bogus_value += record.amount
                            bogus_purchase_amounts[record.pan] = bogus_purchase_amounts.get(record.pan, 0) + record.amount
                            logger.debug(f"Node {pan}: Added ₹{record.amount:,.2f} purchase from bogus child {record.pan}")
                            
                except Exception as e:
                    logger.warning(f"Could not read file for {pan} to calculate bogus value: {e}")
            
            # Perform contamination analysis
            self._analyze_contamination(node_data, results, bogus_value, bogus_purchase_amounts)
        
        # Additional step: Mark nodes as bogus if bogus exposure >= 50%
        self._mark_high_exposure_as_bogus(results)
        
        # Additional step: Mark nodes as bogus if they have sales but no/minimal purchases
        self._mark_sales_without_purchases_as_bogus(results)
        
        # Additional step: Mark nodes as bogus based on abnormal P/S ratios
        self._mark_abnormal_ps_ratio_as_bogus(results)
        
        # Final step: Recalculate bogus values after all bogus detection methods
        self._recalculate_bogus_values(results)
        
        # Final step: Recalculate contamination levels after all bogus detection methods
        self._recalculate_contamination_levels(results)
        
        # Log summary
        nodes_with_bogus_value = sum(1 for node in results.values() if node.bogus_value > 0)
        contaminated_nodes = sum(1 for node in results.values() if node.is_contaminated)
        total_bogus_value = sum(node.bogus_value for node in results.values())
        
        logger.info(f"Bogus value calculation complete: {nodes_with_bogus_value} nodes have bogus values totaling ₹{total_bogus_value:,.2f}")
        logger.info(f"Contamination analysis complete: {contaminated_nodes} nodes are contaminated (all/majority children bogus)")
    
    def _analyze_contamination(self, node_data: NodeData, results: Dict[str, NodeData], 
                              bogus_value: float, bogus_purchase_amounts: Dict[str, float]) -> None:
        """
        Analyze contamination based on the value of purchases from bogus children.
        Update bogus value by aggregating purchases from bogus children regardless of parent's P/S ratio.
        
        Args:
            node_data: The node to analyze
            results: All processed nodes
            bogus_value: Total bogus value calculated from purchases to bogus children
            bogus_purchase_amounts: Individual purchase amounts to bogus children
        """
        if not node_data.children:
            # No children, no contamination
            node_data.bogus_value = bogus_value
            node_data.adjusted_purchases = node_data.total_purchases
            node_data.contamination_level = 0.0
            node_data.is_contaminated = False
            return
        
        # Calculate total purchases to all children (for contamination percentage)
        total_purchases_to_children = 0.0
        bogus_purchases_to_children = 0.0
        
        # We need to calculate purchases to ALL children, not just bogus ones
        # The bogus_purchase_amounts only contains purchases to bogus children
        # So we need to read the actual transaction data to get total purchases to all children
        
        # For now, use the bogus_purchase_amounts as a proxy for total purchases to children
        # This assumes that most significant purchases are captured in the bogus analysis
        for child_pan in node_data.children:
            if child_pan in bogus_purchase_amounts:
                purchase_amount = bogus_purchase_amounts[child_pan]
                total_purchases_to_children += purchase_amount
                
                # If child is bogus, add to bogus purchases
                if child_pan in results and results[child_pan].is_bogus:
                    bogus_purchases_to_children += purchase_amount
        
        # Set bogus value to the aggregated purchases from bogus children (regardless of parent's P/S ratio)
        node_data.bogus_value = bogus_value
        
        # Calculate contamination level based on bogus value vs total purchases
        # This gives us the percentage of total purchases that are bogus
        # Note: This will be recalculated later after all bogus detection methods are applied
        if node_data.total_purchases > 0:
            contamination_level = (bogus_value / node_data.total_purchases) * 100
        else:
            contamination_level = 100
        
        node_data.contamination_level = contamination_level
        
        # Check if node is contaminated (>50% of purchase value goes to bogus children)
        is_contaminated = contamination_level > 10.0
        node_data.is_contaminated = is_contaminated
        
        if is_contaminated:
            # Node is contaminated - adjust purchases and P/S ratio
            bogus_children = [child_pan for child_pan in node_data.children 
                             if child_pan in results and results[child_pan].is_bogus]
            total_children = len(node_data.children)
            bogus_children_count = len(bogus_children)
            
            logger.info(f"Node {node_data.pan} is CONTAMINATED: {contamination_level:.1f}% of purchases (₹{bogus_purchases_to_children:,.2f}/₹{total_purchases_to_children:,.2f}) go to {bogus_children_count}/{total_children} bogus children")
            
            # Remove bogus purchases from total purchases
            adjusted_purchases = node_data.total_purchases - bogus_value
            node_data.adjusted_purchases = max(0, adjusted_purchases)  # Ensure non-negative
            
            # Recalculate P/S ratio with adjusted purchases
            if node_data.total_sales > 0:
                node_data.purchase_to_sales_ratio = node_data.adjusted_purchases / node_data.total_sales
            else:
                node_data.purchase_to_sales_ratio = float('inf') if node_data.adjusted_purchases > 0 else 0
            
            logger.debug(f"Node {node_data.pan}: Original purchases ₹{node_data.total_purchases:,.2f} → "
                        f"Adjusted purchases ₹{node_data.adjusted_purchases:,.2f} (removed ₹{bogus_value:,.2f} bogus)")
        else:
            # Node is not contaminated - keep original values but track bogus value
            node_data.adjusted_purchases = node_data.total_purchases
            
            if bogus_value > 0:
                bogus_children_count = len([child_pan for child_pan in node_data.children 
                                          if child_pan in results and results[child_pan].is_bogus])
                total_children = len(node_data.children)
                
                logger.debug(f"Node {node_data.pan}: Not contaminated ({contamination_level:.1f}% contamination), "
                           f"but tracking ₹{bogus_value:,.2f} bogus value from {bogus_children_count}/{total_children} bogus children")
    
    def _mark_high_exposure_as_bogus(self, results: Dict[str, NodeData]) -> None:
        """
        Mark nodes as bogus if their bogus exposure is >= 50% of total purchases.
        
        Args:
            results: Dictionary of all processed nodes
        """
        logger.info("Checking for high bogus exposure nodes (≥50%) to mark as bogus...")
        
        newly_marked_bogus = 0
        
        for pan, node_data in results.items():
            # Skip if already marked as bogus
            if node_data.is_bogus:
                continue
                
            # Check if bogus exposure >= 50%
            if node_data.total_purchases > 0 and node_data.bogus_value > 0:
                bogus_exposure_percentage = (node_data.bogus_value / node_data.total_purchases) * 100
                
                if bogus_exposure_percentage >= 50.0:
                    # Mark as bogus due to high exposure
                    node_data.is_bogus = True
                    newly_marked_bogus += 1
                    
                    logger.info(f"Node {pan} marked as BOGUS due to high exposure: "
                              f"₹{node_data.bogus_value:,.2f} / ₹{node_data.total_purchases:,.2f} ({bogus_exposure_percentage:.1f}%)")
        
        if newly_marked_bogus > 0:
            logger.info(f"Marked {newly_marked_bogus} additional nodes as bogus due to high exposure (≥50%)")
        else:
            logger.info("No additional nodes marked as bogus due to high exposure")
    
    def _mark_sales_without_purchases_as_bogus(self, results: Dict[str, NodeData]) -> None:
        """
        Mark nodes as bogus if they have sales but no purchases.
        For such nodes, set the entire sales value as bogus value.
        
        Args:
            results: Dictionary of all processed nodes
        """
        logger.info("Checking for nodes with sales but no purchases...")
        
        newly_marked_bogus = 0
        total_sales_marked_bogus = 0
        updated_bogus_values = 0
        
        for pan, node_data in results.items():
            # Check if node has sales but NO purchases (exactly 0)
            if node_data.total_sales > 0 and node_data.total_purchases == 0:
                
                # Set the entire sales value as bogus value
                original_bogus_value = node_data.bogus_value
                node_data.bogus_value = node_data.total_sales
                
                if not node_data.is_bogus:
                    # Mark as bogus if not already marked
                    node_data.is_bogus = True
                    newly_marked_bogus += 1
                    
                    logger.info(f"Node {pan} marked as BOGUS due to sales without purchases: "
                              f"Sales ₹{node_data.total_sales:,.2f}, Purchases ₹0. "
                              f"Bogus value: ₹{original_bogus_value:,.2f} → ₹{node_data.bogus_value:,.2f}")
                else:
                    # Already bogus, just update bogus value
                    updated_bogus_values += 1
                    
                    logger.info(f"Node {pan} (already bogus) updated bogus value due to sales without purchases: "
                              f"Sales ₹{node_data.total_sales:,.2f}, Purchases ₹0. "
                              f"Bogus value: ₹{original_bogus_value:,.2f} → ₹{node_data.bogus_value:,.2f}")
                
                total_sales_marked_bogus += node_data.total_sales
        
        if newly_marked_bogus > 0 or updated_bogus_values > 0:
            logger.info(f"Sales-without-purchases processing complete:")
            logger.info(f"  - Newly marked as bogus: {newly_marked_bogus} nodes")
            logger.info(f"  - Updated bogus values: {updated_bogus_values} nodes")
            logger.info(f"  - Total sales value set as bogus: ₹{total_sales_marked_bogus:,.2f}")
        else:
            logger.info("No nodes found with sales but no purchases")
    
    def _mark_abnormal_ps_ratio_as_bogus(self, results: Dict[str, NodeData]) -> None:
        """
        Mark nodes as bogus based on abnormal Purchase-to-Sales ratios:
        - P/S ratio < 0.2 (purchases < 20% of sales): Mark sales value as bogus
        - P/S ratio > 3.0 (purchases > 300% of sales): Mark purchase value as bogus
        
        Args:
            results: Dictionary of all processed nodes
        """
        logger.info("Checking for nodes with abnormal P/S ratios...")
        
        low_ratio_nodes = 0  # P/S < 0.2
        high_ratio_nodes = 0  # P/S > 3.0
        total_sales_marked_bogus = 0
        total_purchases_marked_bogus = 0
        
        for pan, node_data in results.items():
            # Skip nodes with no sales or purchases
            if node_data.total_sales <= 0 or node_data.total_purchases <= 0:
                continue
                
            # Calculate P/S ratio
            ps_ratio = node_data.total_purchases / node_data.total_sales
            
            # Check for abnormally low P/S ratio (< 0.2)
            if ps_ratio < 0.2:
                # Mark sales value as bogus (entity selling much more than purchasing)
                original_bogus_value = node_data.bogus_value
                
                # Add sales value to existing bogus value (don't replace, accumulate)
                node_data.bogus_value = max(node_data.bogus_value, node_data.total_sales)
                
                if not node_data.is_bogus:
                    node_data.is_bogus = True
                    low_ratio_nodes += 1
                    
                    logger.info(f"Node {pan} marked as BOGUS due to low P/S ratio: "
                              f"P/S = {ps_ratio:.4f} (<0.2). Sales ₹{node_data.total_sales:,.2f} marked as bogus. "
                              f"Bogus value: ₹{original_bogus_value:,.2f} → ₹{node_data.bogus_value:,.2f}")
                else:
                    # Already bogus, just update bogus value if sales is higher
                    if node_data.total_sales > original_bogus_value:
                        logger.info(f"Node {pan} (already bogus) updated bogus value due to low P/S ratio: "
                                  f"P/S = {ps_ratio:.4f} (<0.2). "
                                  f"Bogus value: ₹{original_bogus_value:,.2f} → ₹{node_data.bogus_value:,.2f}")
                
                total_sales_marked_bogus += node_data.total_sales
            
            # Check for abnormally high P/S ratio (> 3.0)
            elif ps_ratio > 3.0:
                # Mark purchase value as bogus (entity purchasing much more than selling)
                original_bogus_value = node_data.bogus_value
                
                # Add purchase value to existing bogus value (don't replace, accumulate)
                node_data.bogus_value = max(node_data.bogus_value, node_data.total_purchases)
                
                if not node_data.is_bogus:
                    node_data.is_bogus = True
                    high_ratio_nodes += 1
                    
                    logger.info(f"Node {pan} marked as BOGUS due to high P/S ratio: "
                              f"P/S = {ps_ratio:.4f} (>3.0). Purchases ₹{node_data.total_purchases:,.2f} marked as bogus. "
                              f"Bogus value: ₹{original_bogus_value:,.2f} → ₹{node_data.bogus_value:,.2f}")
                else:
                    # Already bogus, just update bogus value if purchases is higher
                    if node_data.total_purchases > original_bogus_value:
                        logger.info(f"Node {pan} (already bogus) updated bogus value due to high P/S ratio: "
                                  f"P/S = {ps_ratio:.4f} (>3.0). "
                                  f"Bogus value: ₹{original_bogus_value:,.2f} → ₹{node_data.bogus_value:,.2f}")
                
                total_purchases_marked_bogus += node_data.total_purchases
        
        if low_ratio_nodes > 0 or high_ratio_nodes > 0:
            logger.info(f"Abnormal P/S ratio processing complete:")
            logger.info(f"  - Low P/S ratio nodes (P/S < 0.2): {low_ratio_nodes} nodes")
            logger.info(f"  - High P/S ratio nodes (P/S > 3.0): {high_ratio_nodes} nodes")
            logger.info(f"  - Total sales value marked as bogus: ₹{total_sales_marked_bogus:,.2f}")
            logger.info(f"  - Total purchases value marked as bogus: ₹{total_purchases_marked_bogus:,.2f}")
        else:
            logger.info("No nodes found with abnormal P/S ratios")
    
    def _recalculate_contamination_levels(self, results: Dict[str, NodeData]) -> None:
        """
        Recalculate contamination levels after all bogus detection methods have been applied.
        This ensures contamination percentages reflect the final bogus values from all sources.
        
        Args:
            results: Dictionary of all processed nodes
        """
        logger.info("Recalculating contamination levels after all bogus detection methods...")
        
        contamination_updates = 0
        
        for pan, node_data in results.items():
            if node_data.total_purchases > 0 and node_data.bogus_value > 0:
                # Calculate final contamination level based on final bogus value
                final_contamination_level = min(100.0, (node_data.bogus_value / node_data.total_purchases) * 100)
                
                # Update if different from current contamination level
                if abs(final_contamination_level - node_data.contamination_level) > 0.1:
                    original_contamination = node_data.contamination_level
                    node_data.contamination_level = final_contamination_level
                    
                    # Update contamination status
                    original_contaminated = node_data.is_contaminated
                    node_data.is_contaminated = final_contamination_level > 50.0
                    
                    contamination_updates += 1
                    
                    logger.debug(f"Node {pan}: Contamination updated from {original_contamination:.1f}% to {final_contamination_level:.1f}% "
                               f"(contaminated: {original_contaminated} → {node_data.is_contaminated})")
        
        if contamination_updates > 0:
            logger.info(f"Updated contamination levels for {contamination_updates} nodes after final bogus value calculation")
        else:
            logger.info("No contamination level updates needed")
    
    def _recalculate_bogus_values(self, results: Dict[str, NodeData]) -> None:
        """
        Recalculate bogus values after all bogus detection methods have been applied.
        This ensures that purchases to entities marked as bogus by later methods are captured.
        
        Args:
            results: Dictionary of all processed nodes
        """
        logger.info("Recalculating bogus values after all bogus detection methods...")
        
        bogus_value_updates = 0
        
        for pan, node_data in results.items():
            original_bogus_value = node_data.bogus_value
            new_bogus_value = 0.0
            
            # Read the node's own file to get transaction details
            if pan in self.file_mapping:
                data_dir = self.config.get('data_directory', 'data/input')
                file_path = os.path.join(data_dir, self.file_mapping[pan])
                
                try:
                    records = self._read_excel_data(file_path)
                    
                    # Check each transaction record
                    for record in records:
                        # If this record is a purchase (GSTR1-P) from a now-bogus entity
                        if (record.transaction_type == 'GSTR1-P' and 
                            record.pan in results and
                            results[record.pan].is_bogus):
                            
                            # Add the actual purchase amount paid to this bogus entity
                            new_bogus_value += record.amount
                            
                except Exception as e:
                    logger.warning(f"Could not read file for {pan} to recalculate bogus value: {e}")
                    # Keep the original bogus value if we can't read the file
                    new_bogus_value = original_bogus_value
            else:
                # Keep the original bogus value if no file mapping
                new_bogus_value = original_bogus_value
            
            # Update bogus value if it changed significantly
            if abs(new_bogus_value - original_bogus_value) > 1.0:  # Allow for small rounding differences
                node_data.bogus_value = new_bogus_value
                bogus_value_updates += 1
                
                logger.debug(f"Node {pan}: Bogus value updated from ₹{original_bogus_value:,.2f} to ₹{new_bogus_value:,.2f}")
        
        if bogus_value_updates > 0:
            logger.info(f"Updated bogus values for {bogus_value_updates} nodes after final bogus detection")
        else:
            logger.info("No bogus value updates needed")
    
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
            
            # Calculate bogus values for all nodes
            self._calculate_bogus_values(results)
            
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
        contaminated_nodes = sum(1 for node in results.values() if node.is_contaminated)
        total_sales = sum(node.total_sales for node in results.values())
        total_purchases = sum(node.total_purchases for node in results.values())
        total_adjusted_purchases = sum(node.adjusted_purchases for node in results.values())
        total_bogus_value = sum(node.bogus_value for node in results.values())
        nodes_with_bogus_value = sum(1 for node in results.values() if node.bogus_value > 0)
        
        report.append("SUMMARY STATISTICS:")
        report.append(f"Total Nodes Analyzed: {total_nodes}")
        report.append(f"Bogus Nodes Detected: {bogus_nodes} ({bogus_nodes/total_nodes*100:.1f}%)")
        report.append(f"Contaminated Nodes: {contaminated_nodes} ({contaminated_nodes/total_nodes*100:.1f}%)")
        report.append(f"Nodes with Bogus Value: {nodes_with_bogus_value} ({nodes_with_bogus_value/total_nodes*100:.1f}%)")
        report.append(f"Total Sales Amount: ₹{total_sales:,.2f}")
        report.append(f"Total Purchases Amount: ₹{total_purchases:,.2f}")
        report.append(f"Total Adjusted Purchases: ₹{total_adjusted_purchases:,.2f}")
        report.append(f"Total Bogus Value: ₹{total_bogus_value:,.2f}")
        report.append(f"Overall P/S Ratio (Original): {total_purchases/total_sales:.4f}" if total_sales > 0 else "Overall P/S Ratio (Original): N/A")
        report.append(f"Overall P/S Ratio (Adjusted): {total_adjusted_purchases/total_sales:.4f}" if total_sales > 0 else "Overall P/S Ratio (Adjusted): N/A")
        report.append("")
        
        # Contamination analysis
        contamination_distribution = defaultdict(int)
        for node in results.values():
            if node.contamination_level >= 80:
                contamination_distribution['Very High'] += 1
            elif node.contamination_level >= 60:
                contamination_distribution['High'] += 1
            elif node.contamination_level >= 40:
                contamination_distribution['Medium'] += 1
            elif node.contamination_level >= 20:
                contamination_distribution['Low'] += 1
            else:
                contamination_distribution['None'] += 1
        
        report.append("CONTAMINATION DISTRIBUTION:")
        for contamination_level, count in contamination_distribution.items():
            percentage = (count / total_nodes) * 100
            report.append(f"{contamination_level} Contamination: {count} nodes ({percentage:.1f}%)")
        report.append("")
        
        # Detailed node analysis
        report.append("DETAILED ANALYSIS:")
        report.append("-" * 150)
        report.append(f"{'PAN':<15} {'Sales':<15} {'Purchases':<15} {'Adj.Purch':<15} {'Bogus Value':<15} {'P/S Ratio':<10} {'Status':<8} {'Contam%':<8} {'Children'}")
        report.append("-" * 150)
        
        # Sort by contamination level (highest first)
        sorted_results = sorted(results.items(), key=lambda x: x[1].contamination_level, reverse=True)
        
        for pan, node in sorted_results:
            if node.is_bogus:
                status = "BOGUS"
            elif node.is_contaminated:
                status = "CONTAM"
            else:
                status = "OK"
            
            children_count = len(node.children)
            ratio_str = f"{node.purchase_to_sales_ratio:.4f}" if node.purchase_to_sales_ratio != float('inf') else "∞"
            contam_str = f"{node.contamination_level:.1f}%" if node.contamination_level > 0 else "-"
            
            report.append(f"{pan:<15} {node.total_sales:<15,.0f} {node.total_purchases:<15,.0f} "
                         f"{node.adjusted_purchases:<15,.0f} {node.bogus_value:<15,.0f} {ratio_str:<10} "
                         f"{status:<8} {contam_str:<8} {children_count}")
        
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
                    'Original_Total_Purchases': node.original_total_purchases,
                    'Adjusted_Purchases': node.adjusted_purchases,
                    'Purchase_to_Sales_Ratio': node.purchase_to_sales_ratio,
                    'Is_Bogus': node.is_bogus,
                    'Bogus_Value': node.bogus_value,
                    'Is_Contaminated': node.is_contaminated,
                    'Contamination_Level': node.contamination_level,
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
