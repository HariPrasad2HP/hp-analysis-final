#!/usr/bin/env python3
"""
Web Server Startup Script

Starts the Flask web server for the GST Analysis System web interface.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add src directory and project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, project_root)

from web.app import create_app
from utils.logger import setup_logger
from config.config import ConfigManager, get_config_for_environment

def main():
    """Main function to start the web server"""
    parser = argparse.ArgumentParser(
        description='GST Analysis System Web Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_server.py                    # Start with default settings
  python start_server.py --port 8080       # Use custom port
  python start_server.py --debug           # Enable debug mode
  python start_server.py --host 0.0.0.0    # Allow external connections
        """
    )
    
    parser.add_argument('--config', type=str,
                       help='Path to configuration file')
    parser.add_argument('--env', type=str, default='development',
                       choices=['development', 'production', 'testing'],
                       help='Environment configuration to use')
    parser.add_argument('--host', type=str,
                       help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int,
                       help='Port to bind to (default: 8000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--no-reload', action='store_true',
                       help='Disable auto-reload in debug mode')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    try:
        # Setup logging
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
        host = args.host or config.web_host
        port = args.port or config.web_port
        debug = args.debug or config.web_debug
        
        if args.log_level:
            config.log_level = args.log_level
        
        logger.info("Starting GST Analysis System Web Server")
        logger.info(f"Environment: {args.env}")
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Debug Mode: {debug}")
        
        # Create Flask application
        app = create_app(config)
        
        # Start the server
        logger.info("Server starting...")
        logger.info(f"Access the application at: http://{host}:{port}")
        
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug and not args.no_reload,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
