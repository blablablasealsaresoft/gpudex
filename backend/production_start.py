#!/usr/bin/env python3
"""
GPUDex Production Startup Script
Handles production deployment with proper logging, worker management, and monitoring.
"""

import os
import sys
import logging
import multiprocessing
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/gpudex.log', mode='a') if os.path.exists('/app/logs') else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_workers():
    """Calculate optimal number of workers based on CPU cores."""
    workers = int(os.getenv('WORKERS', 0))
    if workers <= 0:
        workers = min(multiprocessing.cpu_count() * 2 + 1, 8)  # Cap at 8 workers
    return workers

def validate_environment():
    """Validate required environment variables."""
    required_vars = [
        'DATABASE_URL',
        'ENVIRONMENT'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    logger.info("Environment validation passed")

def setup_database():
    """Initialize database tables if needed."""
    try:
        from database import DatabaseManager, create_tables
        db_manager = DatabaseManager()
        create_tables()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

def start_application():
    """Start the FastAPI application with Gunicorn."""
    import uvicorn
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    workers = get_workers()
    log_level = os.getenv('LOG_LEVEL', 'info')
    
    logger.info(f"Starting GPUDex API server")
    logger.info(f"Host: {host}:{port}")
    logger.info(f"Workers: {workers}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT')}")
    logger.info(f"Log Level: {log_level}")
    
    # Start server with Gunicorn for production
    if workers > 1:
        # Use Gunicorn for multi-worker production deployment
        os.system(f"""
            gunicorn api:app \
                --bind {host}:{port} \
                --workers {workers} \
                --worker-class uvicorn.workers.UvicornWorker \
                --worker-connections 1000 \
                --max-requests 1000 \
                --max-requests-jitter 100 \
                --timeout 30 \
                --keep-alive 5 \
                --log-level {log_level} \
                --access-logfile - \
                --error-logfile - \
                --capture-output
        """)
    else:
        # Use Uvicorn for single worker (development/testing)
        uvicorn.run(
            "api:app",
            host=host,
            port=port,
            log_level=log_level,
            reload=False,
            workers=1
        )

def main():
    """Main entry point for production startup."""
    try:
        logger.info("🚀 Starting GPUDex Production Server")
        
        # Validate environment
        validate_environment()
        
        # Initialize database
        setup_database()
        
        # Start application
        start_application()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 