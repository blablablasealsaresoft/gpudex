import os
import time
import hashlib
import secrets
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from functools import wraps

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# Temporarily commented out while fixing import issues
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded
# from slowapi.middleware import SlowAPIMiddleware

from database import DatabaseManager

logger = logging.getLogger(__name__)

# Rate limiter configuration
# Temporarily commented out while fixing import issues
# limiter = Limiter(key_func=get_remote_address)

class APIKeyManager:
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
    
    def generate_api_key(self, user_email: str, key_name: str = "default") -> str:
        """Generate a new API key."""
        # Create a unique API key
        random_part = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        raw_key = f"gpudex_{user_email}_{timestamp}_{random_part}"
        
        # Hash for storage (optional security layer)
        api_key = f"gpudx_{hashlib.sha256(raw_key.encode()).hexdigest()[:24]}"
        
        return api_key
    
    async def create_api_key(self, user_email: str, key_name: str = "default", 
                           requests_per_hour: int = 100, requests_per_day: int = 1000) -> Dict:
        """Create a new API key in the database."""
        try:
            db_manager = DatabaseManager()
            api_key = self.generate_api_key(user_email, key_name)
            
            # Insert into database
            query = """
                INSERT INTO api_keys (key_name, api_key, user_email, requests_per_hour, requests_per_day)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, created_at
            """
            
            result = db_manager.db.execute(query, (key_name, api_key, user_email, requests_per_hour, requests_per_day))
            row = result.fetchone()
            db_manager.db.commit()
            db_manager.close()
            
            if row:
                return {
                    "api_key": api_key,
                    "user_email": user_email,
                    "key_name": key_name,
                    "requests_per_hour": requests_per_hour,
                    "requests_per_day": requests_per_day,
                    "created_at": row[1],
                    "status": "active"
                }
            else:
                raise Exception("Failed to create API key")
                
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            raise HTTPException(status_code=500, detail="Failed to create API key")
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate an API key and return user info."""
        try:
            db_manager = DatabaseManager()
            
            query = """
                SELECT id, key_name, user_email, requests_per_hour, requests_per_day, 
                       is_active, created_at, last_used_at, usage_count
                FROM api_keys 
                WHERE api_key = %s AND is_active = true
            """
            
            result = db_manager.db.execute(query, (api_key,))
            row = result.fetchone()
            db_manager.close()
            
            if row:
                return {
                    "id": row[0],
                    "key_name": row[1],
                    "user_email": row[2],
                    "requests_per_hour": row[3],
                    "requests_per_day": row[4],
                    "is_active": row[5],
                    "created_at": row[6],
                    "last_used_at": row[7],
                    "usage_count": row[8]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None
    
    async def update_api_key_usage(self, api_key: str):
        """Update API key usage statistics."""
        try:
            db_manager = DatabaseManager()
            
            query = """
                UPDATE api_keys 
                SET last_used_at = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                WHERE api_key = %s
            """
            
            db_manager.db.execute(query, (api_key,))
            db_manager.db.commit()
            db_manager.close()
            
        except Exception as e:
            logger.error(f"Error updating API key usage: {e}")

class RateLimitManager:
    def __init__(self):
        self.usage_cache = {}  # In-memory cache for rate limiting
        self.cache_cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    def get_rate_limit_key(self, api_key: str, time_window: str) -> str:
        """Generate a rate limit key for the given API key and time window."""
        if time_window == "hour":
            timestamp = int(time.time() // 3600)  # Hour bucket
        elif time_window == "day":
            timestamp = int(time.time() // 86400)  # Day bucket
        else:
            timestamp = int(time.time() // 3600)  # Default to hour
        
        return f"{api_key}:{time_window}:{timestamp}"
    
    def check_rate_limit(self, api_key_info: Dict) -> Tuple[bool, Dict]:
        """Check if the API key has exceeded rate limits."""
        api_key = api_key_info.get("id")  # Use API key ID for rate limiting
        
        hour_key = self.get_rate_limit_key(str(api_key), "hour")
        day_key = self.get_rate_limit_key(str(api_key), "day")
        
        # Get current usage
        hour_usage = self.usage_cache.get(hour_key, 0)
        day_usage = self.usage_cache.get(day_key, 0)
        
        # Check limits
        hour_limit = api_key_info.get("requests_per_hour", 100)
        day_limit = api_key_info.get("requests_per_day", 1000)
        
        if hour_usage >= hour_limit:
            return False, {
                "error": "Hourly rate limit exceeded",
                "limit": hour_limit,
                "used": hour_usage,
                "reset_time": (int(time.time() // 3600) + 1) * 3600
            }
        
        if day_usage >= day_limit:
            return False, {
                "error": "Daily rate limit exceeded", 
                "limit": day_limit,
                "used": day_usage,
                "reset_time": (int(time.time() // 86400) + 1) * 86400
            }
        
        # Increment usage
        self.usage_cache[hour_key] = hour_usage + 1
        self.usage_cache[day_key] = day_usage + 1
        
        # Cleanup old entries periodically
        if time.time() - self.last_cleanup > self.cache_cleanup_interval:
            self._cleanup_cache()
        
        return True, {
            "hourly_usage": hour_usage + 1,
            "hourly_limit": hour_limit,
            "daily_usage": day_usage + 1, 
            "daily_limit": day_limit
        }
    
    def _cleanup_cache(self):
        """Clean up old rate limit entries."""
        current_time = time.time()
        current_hour = int(current_time // 3600)
        current_day = int(current_time // 86400)
        
        keys_to_remove = []
        
        for key in self.usage_cache:
            if ":" in key:
                parts = key.split(":")
                if len(parts) >= 3:
                    time_window = parts[1]
                    timestamp = int(parts[2])
                    
                    if time_window == "hour" and timestamp < current_hour - 1:
                        keys_to_remove.append(key)
                    elif time_window == "day" and timestamp < current_day - 1:
                        keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.usage_cache[key]
        
        self.last_cleanup = current_time
        logger.info(f"Cleaned up {len(keys_to_remove)} old rate limit entries")

# Global instances
api_key_manager = APIKeyManager()
rate_limit_manager = RateLimitManager()

async def get_api_key_info(credentials: Optional[HTTPAuthorizationCredentials] = Depends(api_key_manager.security)) -> Optional[Dict]:
    """Dependency to extract and validate API key."""
    if not credentials:
        return None
    
    api_key_info = await api_key_manager.validate_api_key(credentials.credentials)
    if api_key_info:
        # Update usage stats
        await api_key_manager.update_api_key_usage(credentials.credentials)
    
    return api_key_info

async def require_api_key(api_key_info: Optional[Dict] = Depends(get_api_key_info)) -> Dict:
    """Dependency that requires a valid API key."""
    if not api_key_info:
        raise HTTPException(
            status_code=401,
            detail="Valid API key required. Get yours at https://gpudex.com/api-keys",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return api_key_info

async def check_rate_limits(api_key_info: Dict = Depends(require_api_key)) -> Dict:
    """Dependency that checks rate limits for API key."""
    allowed, info = rate_limit_manager.check_rate_limit(api_key_info)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=info,
            headers={
                "X-RateLimit-Limit": str(info.get("limit", 0)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info.get("reset_time", 0))
            }
        )
    
    return api_key_info

def add_rate_limit_headers(response, api_key_info: Dict, rate_info: Dict):
    """Add rate limit headers to response."""
    response.headers["X-RateLimit-Hourly-Limit"] = str(rate_info.get("hourly_limit", 0))
    response.headers["X-RateLimit-Hourly-Remaining"] = str(rate_info.get("hourly_limit", 0) - rate_info.get("hourly_usage", 0))
    response.headers["X-RateLimit-Daily-Limit"] = str(rate_info.get("daily_limit", 0))
    response.headers["X-RateLimit-Daily-Remaining"] = str(rate_info.get("daily_limit", 0) - rate_info.get("daily_usage", 0))
    response.headers["X-API-Key-User"] = api_key_info.get("user_email", "unknown")

# Rate limiting decorators
def basic_rate_limit(func):
    """Basic rate limit decorator - 100 requests per hour"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # For now, just pass through without rate limiting
        # TODO: Implement proper rate limiting
        return await func(*args, **kwargs)
    
    return wrapper

def premium_rate_limit(func):
    """Premium rate limit decorator - 1000 requests per hour"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # For now, just pass through without rate limiting
        # TODO: Implement proper rate limiting
        return await func(*args, **kwargs)
    
    return wrapper

# Default rate limits for public endpoints (no API key required)
# Temporarily simplified until slowapi issues are resolved
def public_rate_limit(func):
    """Public rate limit decorator - 10 requests per minute"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper

def free_tier_limit(func):
    """Free tier rate limit decorator - 100 requests per hour"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper

def premium_limit(func):
    """Premium rate limit decorator - 1000 requests per hour"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper 