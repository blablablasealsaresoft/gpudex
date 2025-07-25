#!/usr/bin/env python3
"""
Render-specific startup script for GPUDex backend
"""

import os
import sys
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main startup function for Render"""
    try:
        # Import after path setup
        from api import app
        import uvicorn
        
        # Get port from environment variable (Render sets this)
        port = int(os.environ.get("PORT", 8000))
        
        logger.info(f"Starting GPUDex API server on port {port}")
        logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
        
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