"""
GPUDex Redis Caching Service
Advanced caching layer for performance optimization and reduced API calls.
"""

import redis
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import hashlib
import asyncio
from functools import wraps
import os

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to memory cache.")
            self.redis_client = None
            self._memory_cache = {}
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate a unique cache key from parameters"""
        key_data = f"{prefix}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _serialize(self, data: Any) -> str:
        """Serialize data for storage"""
        if isinstance(data, (dict, list)):
            return json.dumps(data, default=str)
        return str(data)
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize data from storage"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                return self._deserialize(value) if value else None
            else:
                return self._memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        try:
            serialized_value = self._serialize(value)
            if self.redis_client:
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                self._memory_cache[key] = serialized_value
                # Simple TTL simulation for memory cache
                asyncio.create_task(self._expire_memory_key(key, ttl))
                return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def _expire_memory_key(self, key: str, ttl: int):
        """Expire memory cache key after TTL"""
        await asyncio.sleep(ttl)
        self._memory_cache.pop(key, None)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                return bool(self._memory_cache.pop(key, None))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # Simple pattern matching for memory cache
                keys_to_delete = [k for k in self._memory_cache.keys() if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                return len(keys_to_delete)
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            else:
                return key in self._memory_cache
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get TTL for key"""
        try:
            if self.redis_client:
                return self.redis_client.ttl(key)
            else:
                return -1  # Memory cache doesn't track TTL
        except Exception as e:
            logger.error(f"Cache TTL error: {e}")
            return -1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', '0B'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0)
                }
            else:
                return {
                    'memory_cache_keys': len(self._memory_cache),
                    'type': 'memory_fallback'
                }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}

# Global cache instance
cache = CacheService()

# Decorators for caching
def cache_result(ttl: int = 300, key_prefix: str = "general"):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and parameters
            cache_key = cache._generate_key(
                f"{key_prefix}:{func.__name__}",
                args=str(args),
                kwargs=str(kwargs)
            )
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}")
            return result
        return wrapper
    return decorator

def cache_prices(ttl: int = 180):
    """Specialized decorator for caching GPU prices"""
    return cache_result(ttl=ttl, key_prefix="prices")

def cache_analytics(ttl: int = 600):
    """Specialized decorator for caching analytics data"""
    return cache_result(ttl=ttl, key_prefix="analytics")

def cache_providers(ttl: int = 3600):
    """Specialized decorator for caching provider data"""
    return cache_result(ttl=ttl, key_prefix="providers")

# Smart caching strategies
class SmartCache:
    """Intelligent caching with different strategies"""
    
    @staticmethod
    def cache_prices_with_strategy(provider: str, gpu_type: str = None):
        """Cache prices with intelligent TTL based on provider volatility"""
        # Different TTL based on provider update frequency
        ttl_map = {
            'aws': 300,      # 5 minutes - frequently updated
            'gcp': 300,      # 5 minutes - frequently updated  
            'azure': 300,    # 5 minutes - frequently updated
            'vultr': 600,    # 10 minutes - less frequent
            'linode': 600,   # 10 minutes - less frequent
            'vast': 180,     # 3 minutes - very dynamic
            'runpod': 180,   # 3 minutes - very dynamic
            'default': 300   # 5 minutes default
        }
        
        ttl = ttl_map.get(provider.lower(), ttl_map['default'])
        key = cache._generate_key("smart_prices", provider=provider, gpu_type=gpu_type or 'all')
        
        return key, ttl
    
    @staticmethod
    def get_cached_prices(provider: str, gpu_type: str = None) -> Optional[Dict]:
        """Get cached prices with smart key generation"""
        key, _ = SmartCache.cache_prices_with_strategy(provider, gpu_type)
        return cache.get(key)
    
    @staticmethod
    def cache_prices_data(provider: str, data: Dict, gpu_type: str = None):
        """Cache prices data with smart strategy"""
        key, ttl = SmartCache.cache_prices_with_strategy(provider, gpu_type)
        cache.set(key, data, ttl)
    
    @staticmethod
    def invalidate_prices(provider: str = None):
        """Invalidate price caches"""
        if provider:
            pattern = f"*smart_prices*provider={provider}*"
        else:
            pattern = "*smart_prices*"
        return cache.clear_pattern(pattern)
    
    @staticmethod
    def warm_cache(providers: List[str], gpu_types: List[str]):
        """Pre-warm cache with common queries"""
        # This would be called by a background task
        logger.info(f"Warming cache for {len(providers)} providers and {len(gpu_types)} GPU types")
        # Implementation would fetch and cache common combinations 