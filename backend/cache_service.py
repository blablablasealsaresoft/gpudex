"""
GPUDex Redis Caching Service
Advanced caching layer for performance optimization and reduced API calls.
"""

import json
import hashlib
import pickle
import logging
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from functools import wraps
import redis
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class CacheService:
    """
    Production-grade Redis caching service with intelligent strategies.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis connection with connection pooling."""
        try:
            # Parse Redis URL and create connection pool
            self.redis_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            self.redis = redis.Redis(connection_pool=self.redis_pool)
            
            # Test connection
            self.redis.ping()
            logger.info("✅ Redis cache service initialized successfully")
            
            # Cache statistics
            self.stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "deletes": 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis cache service: {e}")
            # Fallback to in-memory cache for development
            self.redis = None
            self._memory_cache = {}
            
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key from arguments."""
        # Create a string representation of all arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        
        # Create hash of the data
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]
        
        return f"gpudex:{prefix}:{key_hash}"
    
    def _serialize(self, data: Any) -> bytes:
        """Serialize data for Redis storage."""
        try:
            if isinstance(data, (str, int, float, bool)):
                return json.dumps(data).encode()
            else:
                return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            return pickle.dumps(data)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize data from Redis."""
        try:
            # Try JSON first (faster)
            return json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                # Fall back to pickle
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Deserialization error: {e}")
                return None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis is None:
                # Fallback to memory cache
                result = self._memory_cache.get(key)
                if result:
                    self.stats["hits"] += 1
                else:
                    self.stats["misses"] += 1
                return result
            
            data = self.redis.get(key)
            if data is not None:
                self.stats["hits"] += 1
                return self._deserialize(data)
            else:
                self.stats["misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.stats["misses"] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        try:
            if self.redis is None:
                # Fallback to memory cache (no TTL support)
                self._memory_cache[key] = value
                self.stats["sets"] += 1
                return True
            
            serialized_data = self._serialize(value)
            result = self.redis.setex(key, ttl, serialized_data)
            if result:
                self.stats["sets"] += 1
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.redis is None:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    self.stats["deletes"] += 1
                    return True
                return False
            
            result = self.redis.delete(key)
            if result:
                self.stats["deletes"] += 1
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        try:
            if self.redis is None:
                # Simple pattern matching for memory cache
                keys_to_delete = [k for k in self._memory_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                return len(keys_to_delete)
            
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats["deletes"] += deleted
                return deleted
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear pattern error for pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            if self.redis is None:
                return key in self._memory_cache
            
            return bool(self.redis.exists(key))
            
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> int:
        """Get TTL for a key."""
        try:
            if self.redis is None:
                return -1  # Memory cache doesn't support TTL
            
            return self.redis.ttl(key)
            
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "redis_connected": self.redis is not None,
            "timestamp": datetime.utcnow().isoformat()
        }

# Global cache instance
cache_service = None

def get_cache_service() -> CacheService:
    """Get or create cache service instance."""
    global cache_service
    if cache_service is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cache_service = CacheService(redis_url)
    return cache_service

# Cache decorators for different use cases
def cache_result(prefix: str, ttl: int = 3600):
    """
    Decorator to cache function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_service()
            
            # Generate cache key
            cache_key = cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            if result is not None:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator

def cache_prices(ttl: int = 300):
    """Specialized decorator for caching GPU prices."""
    return cache_result("prices", ttl)

def cache_analytics(ttl: int = 3600):
    """Specialized decorator for caching analytics data."""
    return cache_result("analytics", ttl)

def cache_providers(ttl: int = 1800):
    """Specialized decorator for caching provider data."""
    return cache_result("providers", ttl)

class SmartCache:
    """
    Intelligent caching strategies for different data types.
    """
    
    def __init__(self):
        self.cache = get_cache_service()
    
    async def cache_prices_with_strategy(self, gpu_type: str, region: str, prices: List[Dict]) -> None:
        """
        Cache prices with intelligent strategies:
        - Short TTL for high-demand GPUs
        - Longer TTL for stable prices
        - Different TTLs by region
        """
        
        # Determine TTL based on GPU popularity and volatility
        high_demand_gpus = ["4090", "a100", "h100", "v100"]
        volatile_regions = ["us-east", "eu-west"]
        
        base_ttl = 300  # 5 minutes
        
        if gpu_type.lower() in high_demand_gpus:
            ttl = base_ttl // 2  # 2.5 minutes for high-demand
        else:
            ttl = base_ttl * 2   # 10 minutes for standard GPUs
        
        if region in volatile_regions:
            ttl = int(ttl * 0.8)  # 20% reduction for volatile regions
        
        # Cache with computed TTL
        cache_key = self.cache._generate_key("smart_prices", gpu_type, region)
        await self.cache.set(cache_key, prices, ttl)
        
        # Also cache individual provider prices for partial updates
        for price_data in prices:
            provider_key = self.cache._generate_key("provider_price", price_data.get("provider"), gpu_type, region)
            await self.cache.set(provider_key, price_data, ttl * 2)  # Longer TTL for individual providers
    
    async def get_cached_prices(self, gpu_type: str, region: str) -> Optional[List[Dict]]:
        """Get cached prices with fallback strategies."""
        
        # Try main cache first
        cache_key = self.cache._generate_key("smart_prices", gpu_type, region)
        cached_prices = await self.cache.get(cache_key)
        
        if cached_prices is not None:
            return cached_prices
        
        # Fallback: Try to reconstruct from individual provider caches
        providers = ["vast", "runpod", "tensordock", "lambda", "paperspace", "aws", "gcp", "azure"]
        partial_prices = []
        
        for provider in providers:
            provider_key = self.cache._generate_key("provider_price", provider, gpu_type, region)
            provider_price = await self.cache.get(provider_key)
            if provider_price:
                partial_prices.append(provider_price)
        
        if partial_prices:
            logger.info(f"Reconstructed prices from {len(partial_prices)} cached providers")
            return partial_prices
        
        return None
    
    async def invalidate_prices(self, gpu_type: Optional[str] = None, region: Optional[str] = None) -> int:
        """Invalidate price caches with optional filtering."""
        
        if gpu_type and region:
            # Specific invalidation
            cache_key = self.cache._generate_key("smart_prices", gpu_type, region)
            await self.cache.delete(cache_key)
            return 1
        elif gpu_type:
            # Invalidate all regions for a GPU type
            return await self.cache.clear_pattern(f"gpudex:smart_prices:*{gpu_type}*")
        else:
            # Invalidate all price caches
            return await self.cache.clear_pattern("gpudex:smart_prices:*")
    
    async def warm_cache(self, popular_combinations: List[Dict]) -> None:
        """Pre-warm cache with popular GPU/region combinations."""
        logger.info("Starting cache warm-up...")
        
        # This would be called with actual price fetching logic
        # For now, we'll just log the intent
        for combo in popular_combinations:
            gpu_type = combo.get("gpu_type")
            region = combo.get("region")
            logger.info(f"Would warm cache for {gpu_type} in {region}")
        
        logger.info("Cache warm-up completed")

# Global smart cache instance
smart_cache = SmartCache() 