#!/usr/bin/env python3
"""
Currency Formatter Utility

Provides Indian currency formatting functions with proper crore/lakh notation.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

class CurrencyFormatter:
    """Indian currency formatter with crore/lakh notation"""
    
    @staticmethod
    def convert_to_number(value):
        """
        Convert string to number, handling various formats
        
        Args:
            value: Value to convert (string, number, or None)
            
        Returns:
            float: Converted number or 0 if conversion fails
        """
        if value is None or value == '':
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                # Remove commas and convert to number
                cleaned = value.replace(',', '').strip()
                num = float(cleaned)
                return num if not pd.isna(num) else 0.0
            except (ValueError, TypeError):
                logger.warning(f"Could not convert '{value}' to number")
                return 0.0
        return 0.0
    
    @staticmethod
    def format_currency(amount):
        """
        Format amount in Indian currency with crore/lakh notation
        
        Args:
            amount: Amount to format
            
        Returns:
            str: Formatted currency string
        """
        # Convert to number if needed
        num_amount = CurrencyFormatter.convert_to_number(amount)
        
        if not num_amount or num_amount == 0:
            return '₹0'
        
        # Handle negative amounts
        is_negative = num_amount < 0
        num_amount = abs(num_amount)
        
        # Indian currency formatting - crores and lakhs
        if num_amount >= 1e7:  # 1 crore or more
            formatted = f"₹{(num_amount / 1e7):.2f} Cr"
        elif num_amount >= 1e5:  # 1 lakh or more
            formatted = f"₹{(num_amount / 1e5):.2f} L"
        elif num_amount >= 1e3:  # 1 thousand or more
            formatted = f"₹{(num_amount / 1e3):.1f}K"
        else:
            formatted = f"₹{round(num_amount):,}"
        
        return f"-{formatted}" if is_negative else formatted
    
    @staticmethod
    def format_currency_compact(amount):
        """
        Format amount in compact Indian currency notation
        
        Args:
            amount: Amount to format
            
        Returns:
            str: Compact formatted currency string
        """
        num_amount = CurrencyFormatter.convert_to_number(amount)
        
        if not num_amount or num_amount == 0:
            return '₹0'
        
        # Handle negative amounts
        is_negative = num_amount < 0
        num_amount = abs(num_amount)
        
        # More compact formatting
        if num_amount >= 1e7:  # 1 crore or more
            formatted = f"₹{(num_amount / 1e7):.1f}Cr"
        elif num_amount >= 1e5:  # 1 lakh or more
            formatted = f"₹{(num_amount / 1e5):.1f}L"
        elif num_amount >= 1e3:  # 1 thousand or more
            formatted = f"₹{(num_amount / 1e3):.0f}K"
        else:
            formatted = f"₹{round(num_amount)}"
        
        return f"-{formatted}" if is_negative else formatted
    
    @staticmethod
    def format_currency_detailed(amount):
        """
        Format amount with detailed Indian currency notation
        
        Args:
            amount: Amount to format
            
        Returns:
            str: Detailed formatted currency string
        """
        num_amount = CurrencyFormatter.convert_to_number(amount)
        
        if not num_amount or num_amount == 0:
            return '₹0.00'
        
        # Handle negative amounts
        is_negative = num_amount < 0
        num_amount = abs(num_amount)
        
        # Detailed formatting with exact values
        if num_amount >= 1e7:  # 1 crore or more
            crores = num_amount / 1e7
            formatted = f"₹{crores:.2f} Crores"
        elif num_amount >= 1e5:  # 1 lakh or more
            lakhs = num_amount / 1e5
            formatted = f"₹{lakhs:.2f} Lakhs"
        elif num_amount >= 1e3:  # 1 thousand or more
            thousands = num_amount / 1e3
            formatted = f"₹{thousands:.2f} Thousands"
        else:
            formatted = f"₹{num_amount:.2f}"
        
        return f"-{formatted}" if is_negative else formatted
    
    @staticmethod
    def parse_indian_currency(currency_str):
        """
        Parse Indian currency string back to number
        
        Args:
            currency_str: Currency string to parse (e.g., "₹10.5 Cr")
            
        Returns:
            float: Parsed amount
        """
        if not currency_str or currency_str == '₹0':
            return 0.0
        
        try:
            # Remove currency symbol and clean up
            cleaned = currency_str.replace('₹', '').strip()
            
            # Handle negative amounts
            is_negative = cleaned.startswith('-')
            if is_negative:
                cleaned = cleaned[1:].strip()
            
            # Parse based on suffix
            if cleaned.endswith(' Cr') or cleaned.endswith('Cr'):
                amount = float(cleaned.replace(' Cr', '').replace('Cr', '')) * 1e7
            elif cleaned.endswith(' L') or cleaned.endswith('L'):
                amount = float(cleaned.replace(' L', '').replace('L', '')) * 1e5
            elif cleaned.endswith('K'):
                amount = float(cleaned.replace('K', '')) * 1e3
            elif cleaned.endswith(' Crores'):
                amount = float(cleaned.replace(' Crores', '')) * 1e7
            elif cleaned.endswith(' Lakhs'):
                amount = float(cleaned.replace(' Lakhs', '')) * 1e5
            elif cleaned.endswith(' Thousands'):
                amount = float(cleaned.replace(' Thousands', '')) * 1e3
            else:
                # Remove commas and parse as regular number
                amount = float(cleaned.replace(',', ''))
            
            return -amount if is_negative else amount
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse currency string '{currency_str}': {e}")
            return 0.0

# Convenience functions for direct use
def format_currency(amount):
    """Format amount in Indian currency"""
    return CurrencyFormatter.format_currency(amount)

def format_currency_compact(amount):
    """Format amount in compact Indian currency"""
    return CurrencyFormatter.format_currency_compact(amount)

def format_currency_detailed(amount):
    """Format amount in detailed Indian currency"""
    return CurrencyFormatter.format_currency_detailed(amount)

def convert_to_number(value):
    """Convert value to number"""
    return CurrencyFormatter.convert_to_number(value)

def parse_indian_currency(currency_str):
    """Parse Indian currency string to number"""
    return CurrencyFormatter.parse_indian_currency(currency_str)
