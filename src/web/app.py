#!/usr/bin/env python3
"""
Flask Web Application

Main web application for the GST Analysis System.
"""

import os
import json
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS

logger = logging.getLogger(__name__)

def create_app(config=None):
    """Create and configure the Flask application"""
    
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(__name__, 
                template_folder=os.path.join(current_dir, 'templates'),
                static_folder=os.path.join(current_dir, 'static'))
    
    # Enable CORS for API endpoints
    CORS(app)
    
    # Configure app
    if config:
        app.config['GST_CONFIG'] = config
        app.config['DEBUG'] = getattr(config, 'web_debug', False)
    
    # Routes
    @app.route('/')
    def index():
        """Main dashboard page"""
        return render_template('dashboard.html')
    
    @app.route('/dashboard')
    def dashboard():
        """Dashboard page"""
        return render_template('dashboard.html')
    
    @app.route('/hierarchy')
    def hierarchy():
        """Hierarchy view page"""
        return render_template('hierarchy.html')
    
    @app.route('/dag')
    def dag():
        """DAG visualization page"""
        return render_template('dag.html')
    
    # API Routes
    @app.route('/api/config')
    def get_config():
        """Get configuration data for frontend"""
        try:
            config = app.config.get('GST_CONFIG')
            if config:
                root_node_pan = getattr(config, 'root_node_pan', '') or 'AAYCA4390A'
                return jsonify({
                    'root_node_pan': root_node_pan,
                    'bogus_threshold': getattr(config, 'bogus_threshold', 0.5),
                    'risk_threshold': getattr(config, 'risk_threshold', 70.0)
                })
            else:
                return jsonify({
                    'root_node_pan': 'AAYCA4390A',
                    'bogus_threshold': 0.5,
                    'risk_threshold': 70.0
                })
        except Exception as e:
            logger.error(f"Error getting configuration: {e}")
            return jsonify({'error': 'Failed to load configuration'}), 500
    
    @app.route('/api/data/<filename>')
    def get_data_file(filename):
        """Serve data files"""
        try:
            config = app.config.get('GST_CONFIG')
            if config:
                data_dir = config.output_directory
            else:
                data_dir = 'data/output'
            
            # Make path absolute
            if not os.path.isabs(data_dir):
                data_dir = os.path.abspath(data_dir)
            
            # Check if file exists
            file_path = os.path.join(data_dir, filename)
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return jsonify({'error': 'File not found'}), 404
            
            return send_from_directory(data_dir, filename)
        except Exception as e:
            logger.error(f"Error serving data file {filename}: {e}")
            return jsonify({'error': 'File not found'}), 404
    
    @app.route('/api/analysis/summary')
    def get_analysis_summary():
        """Get analysis summary statistics"""
        try:
            config = app.config.get('GST_CONFIG')
            if config:
                data_dir = config.output_directory
            else:
                data_dir = 'data/output'
            
            # Load analysis results
            json_file = os.path.join(data_dir, 'gst_table_data.json')
            if not os.path.exists(json_file):
                return jsonify({'error': 'Analysis data not found'}), 404
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Calculate summary statistics
            total_nodes = len(data)
            bogus_nodes = sum(1 for node in data if node.get('Is_Bogus', False))
            contaminated_nodes = sum(1 for node in data if node.get('Is_Contaminated', False))
            total_sales = sum(node.get('Total_Sales', 0) for node in data)
            total_purchases = sum(node.get('Total_Purchases', 0) for node in data)
            total_adjusted_purchases = sum(node.get('Adjusted_Purchases', 0) for node in data)
            total_bogus_value = sum(node.get('Bogus_Value', 0) for node in data)
            nodes_with_bogus_value = sum(1 for node in data if node.get('Bogus_Value', 0) > 0)
            
            # Contamination distribution
            contamination_distribution = {'None': 0, 'Low': 0, 'Medium': 0, 'High': 0, 'Very High': 0}
            for node in data:
                contamination_level = node.get('Contamination_Level', 0)
                if contamination_level >= 80:
                    contamination_distribution['Very High'] += 1
                elif contamination_level >= 60:
                    contamination_distribution['High'] += 1
                elif contamination_level >= 40:
                    contamination_distribution['Medium'] += 1
                elif contamination_level >= 20:
                    contamination_distribution['Low'] += 1
                else:
                    contamination_distribution['None'] += 1
            
            summary = {
                'total_nodes': total_nodes,
                'bogus_nodes': bogus_nodes,
                'bogus_percentage': (bogus_nodes / total_nodes * 100) if total_nodes > 0 else 0,
                'contaminated_nodes': contaminated_nodes,
                'contaminated_percentage': (contaminated_nodes / total_nodes * 100) if total_nodes > 0 else 0,
                'total_sales': total_sales,
                'total_purchases': total_purchases,
                'total_adjusted_purchases': total_adjusted_purchases,
                'total_bogus_value': total_bogus_value,
                'nodes_with_bogus_value': nodes_with_bogus_value,
                'bogus_value_percentage': (nodes_with_bogus_value / total_nodes * 100) if total_nodes > 0 else 0,
                'overall_ps_ratio': (total_purchases / total_sales) if total_sales > 0 else 0,
                'adjusted_ps_ratio': (total_adjusted_purchases / total_sales) if total_sales > 0 else 0,
                'contamination_distribution': contamination_distribution
            }
            
            return jsonify(summary)
            
        except Exception as e:
            logger.error(f"Error getting analysis summary: {e}")
            return jsonify({'error': 'Failed to load analysis summary'}), 500
    
    @app.route('/api/analysis/high-contamination')
    def get_high_contamination_entities():
        """Get high contamination entities"""
        try:
            config = app.config.get('GST_CONFIG')
            if config:
                data_dir = config.output_directory
            else:
                data_dir = 'data/output'
            
            json_file = os.path.join(data_dir, 'gst_table_data.json')
            if not os.path.exists(json_file):
                return jsonify({'error': 'Analysis data not found'}), 404
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Filter and sort high contamination entities
            high_contamination = [node for node in data if node.get('Contamination_Level', 0) > 50]
            high_contamination.sort(key=lambda x: x.get('Contamination_Level', 0), reverse=True)
            
            # Limit to top 20
            high_contamination = high_contamination[:20]
            
            return jsonify(high_contamination)
            
        except Exception as e:
            logger.error(f"Error getting high contamination entities: {e}")
            return jsonify({'error': 'Failed to load high contamination entities'}), 500
    
    @app.route('/api/analysis/search')
    def search_entities():
        """Search entities by PAN or name"""
        try:
            query = request.args.get('q', '').strip().upper()
            if not query:
                return jsonify([])
            
            config = app.config.get('GST_CONFIG')
            if config:
                data_dir = config.output_directory
            else:
                data_dir = 'data/output'
            
            json_file = os.path.join(data_dir, 'gst_table_data.json')
            if not os.path.exists(json_file):
                return jsonify({'error': 'Analysis data not found'}), 404
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Search by PAN
            results = [node for node in data if query in node.get('PAN', '').upper()]
            
            # Limit results
            results = results[:10]
            
            return jsonify(results)
            
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return jsonify({'error': 'Search failed'}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Page not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    # Sales records endpoint
    @app.route('/api/sales/<pan>')
    def get_sales_records(pan):
        """Get all sales records for a specific PAN from JSON data"""
        try:
            config = app.config.get('GST_CONFIG')
            if config:
                data_dir = getattr(config, 'output_directory', 'data/output')
            else:
                data_dir = 'data/output'
            
            # Load analysis results from JSON file
            json_file = os.path.join(data_dir, 'gst_table_data.json')
            if not os.path.exists(json_file):
                return jsonify({'error': 'Analysis data not found'}), 404
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Find the entity data
            entity_data = None
            for item in data:
                if item['PAN'] == pan:
                    entity_data = item
                    break
            
            if not entity_data:
                return jsonify({'error': f'No data found for PAN: {pan}'}), 404
            
            # Get sales records from the stored data
            sales_records = entity_data.get('Sales_Records', [])
            total_sales_amount = sum(record['amount'] for record in sales_records)
            
            return jsonify({
                'seller_pan': pan,
                'seller_name': entity_data.get('Entity_Name', pan),
                'total_sales_records': len(sales_records),
                'total_sales_amount': total_sales_amount,
                'sales_records': sales_records
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Health check
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'GST Analysis System',
            'version': '1.0.0'
        })
    
    logger.info("Flask application created successfully")
    return app

if __name__ == '__main__':
    # For development only
    app = create_app()
    app.run(debug=True, host='localhost', port=8000)
