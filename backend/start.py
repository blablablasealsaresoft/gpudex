#!/usr/bin/env python3
"""
Startup script for GPUDex backend on Render
"""

import os
import sys
import logging
from api import app
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    try:
        # Get port from environment variable (for Render deployment)
        port = int(os.environ.get("PORT", 8000))
        
        logger.info(f"Starting GPUDex API server on port {port}")
        logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
        
        # Run the API server
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 