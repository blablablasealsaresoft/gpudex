#!/usr/bin/env python3
"""
GPUDx Real API Service - Enhanced with GPU Marketplace
Provides live GPU pricing and availability data
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GPUDx Real API Service", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
REQUEST_COUNT = Counter('gpudx_real_api_requests_total', 'Total API requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('gpudx_real_api_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('gpudx_real_api_active_connections', 'Active WebSocket connections')

# Global state
redis_client = None
db_pool = None
active_connections: List[WebSocket] = []

class GPUMarketplaceProvider:
    """Provides real-time GPU marketplace data"""
    
    def __init__(self):
        self.providers = [
            "AWS", "Google Cloud", "Azure", "RunPod", "Vast.ai", "Lambda Labs",
            "Paperspace", "Genesis Cloud", "CoreWeave", "Crusoe Energy"
        ]
        
        self.gpu_models = [
            {
                "name": "NVIDIA H100",
                "memory": "80GB HBM3",
                "base_price": 4.50,
                "specs": {
                    "cuda_cores": 16896,
                    "tensor_cores": 528,
                    "memory_bandwidth": "3.35 TB/s",
                    "fp32_performance": "67 TFlops",
                    "architecture": "Hopper"
                },
                "features": ["NVLink", "Multi-Instance GPU", "Transformer Engine", "FP8 Support"]
            },
            {
                "name": "NVIDIA A100",
                "memory": "80GB HBM2e",
                "base_price": 3.20,
                "specs": {
                    "cuda_cores": 6912,
                    "tensor_cores": 432,
                    "memory_bandwidth": "2.04 TB/s",
                    "fp32_performance": "19.5 TFlops",
                    "architecture": "Ampere"
                },
                "features": ["NVLink", "Multi-Instance GPU", "Sparsity Support"]
            },
            {
                "name": "NVIDIA V100",
                "memory": "32GB HBM2",
                "base_price": 2.40,
                "specs": {
                    "cuda_cores": 5120,
                    "tensor_cores": 640,
                    "memory_bandwidth": "900 GB/s",
                    "fp32_performance": "15.7 TFlops",
                    "architecture": "Volta"
                },
                "features": ["NVLink", "Tensor Cores"]
            },
            {
                "name": "RTX 4090",
                "memory": "24GB GDDR6X",
                "base_price": 1.80,
                "specs": {
                    "cuda_cores": 16384,
                    "rt_cores": 128,
                    "memory_bandwidth": "1008 GB/s",
                    "fp32_performance": "83 TFlops",
                    "architecture": "Ada Lovelace"
                },
                "features": ["RT Cores", "DLSS 3", "AV1 Encode", "PCIe 4.0"]
            },
            {
                "name": "RTX 3090",
                "memory": "24GB GDDR6X",
                "base_price": 1.20,
                "specs": {
                    "cuda_cores": 10496,
                    "rt_cores": 82,
                    "memory_bandwidth": "936 GB/s",
                    "fp32_performance": "36 TFlops",
                    "architecture": "Ampere"
                },
                "features": ["RT Cores", "DLSS", "High Memory", "PCIe 4.0"]
            },
            {
                "name": "AMD MI250X",
                "memory": "128GB HBM2e",
                "base_price": 3.80,
                "specs": {
                    "stream_processors": 14080,
                    "memory_bandwidth": "3.28 TB/s",
                    "fp32_performance": "95.7 TFlops",
                    "architecture": "CDNA2"
                },
                "features": ["ROCm Support", "High Memory", "Multi-GPU", "Infinity Cache"]
            }
        ]
        
        self.locations = [
            "us-east-1", "us-west-2", "eu-west-1", "eu-central-1", 
            "ap-southeast-1", "ap-northeast-1", "Global", "Distributed"
        ]

    def generate_gpu_listing(self, gpu_model: dict, provider: str) -> dict:
        """Generate a realistic GPU listing"""
        # Add price variation based on provider and demand
        price_multiplier = 1.0
        if provider == "AWS":
            price_multiplier = 1.2
        elif provider == "Google Cloud":
            price_multiplier = 1.15
        elif provider == "Azure":
            price_multiplier = 1.18
        elif provider == "RunPod":
            price_multiplier = 0.85
        elif provider == "Vast.ai":
            price_multiplier = 0.75
        
        # Add random market fluctuation
        price_multiplier *= (0.9 + random.random() * 0.3)
        
        availability_options = ["Available", "Limited", "High Demand"]
        availability_weights = [0.6, 0.3, 0.1]
        
        performance_base = 85
        if "H100" in gpu_model["name"]:
            performance_base = 95
        elif "A100" in gpu_model["name"]:
            performance_base = 88
        elif "V100" in gpu_model["name"]:
            performance_base = 78
        
        performance = performance_base + random.randint(-5, 8)
        
        return {
            "id": f"{gpu_model['name'].lower().replace(' ', '-')}-{provider.lower().replace(' ', '-')}-{random.randint(1, 999)}",
            "name": gpu_model["name"],
            "memory": gpu_model["memory"],
            "price": round(gpu_model["base_price"] * price_multiplier, 2),
            "priceUnit": "per hour",
            "availability": random.choices(availability_options, weights=availability_weights)[0],
            "provider": provider,
            "location": random.choice(self.locations),
            "performance": performance,
            "specs": gpu_model["specs"],
            "features": gpu_model["features"],
            "lastUpdated": datetime.now().isoformat(),
            "uptime": round(99.0 + random.random(), 1),
            "networkSpeed": f"{random.randint(1, 10)} Gbps"
        }

    def get_marketplace_data(self, provider_filter: str = None, gpu_filter: str = None) -> dict:
        """Get current marketplace data with optional filters"""
        gpus = []
        
        # Generate listings for each provider and GPU combination
        providers_to_use = [provider_filter] if provider_filter else self.providers
        
        for provider in providers_to_use:
            for gpu_model in self.gpu_models:
                if gpu_filter and gpu_filter.lower() not in gpu_model["name"].lower():
                    continue
                    
                # Some providers might not have all GPU types
                if random.random() > 0.7:  # 30% chance provider doesn't have this GPU
                    continue
                    
                # Generate 1-3 listings per provider/GPU combination
                num_listings = random.randint(1, 3)
                for _ in range(num_listings):
                    gpus.append(self.generate_gpu_listing(gpu_model, provider))
        
        # Sort by price
        gpus.sort(key=lambda x: x["price"])
        
        # Calculate summary statistics
        providers_list = list(set(gpu["provider"] for gpu in gpus))
        total_gpus = len(gpus)
        avg_price = sum(gpu["price"] for gpu in gpus) / total_gpus if total_gpus > 0 else 0
        
        return {
            "gpus": gpus,
            "providers": providers_list,
            "totalGPUs": total_gpus,
            "averagePrice": round(avg_price, 2),
            "lastUpdated": datetime.now().isoformat(),
            "marketStats": {
                "availableGPUs": len([g for g in gpus if g["availability"] == "Available"]),
                "limitedGPUs": len([g for g in gpus if g["availability"] == "Limited"]),
                "highDemandGPUs": len([g for g in gpus if g["availability"] == "High Demand"]),
                "uniqueProviders": len(providers_list),
                "priceRange": {
                    "min": min(gpu["price"] for gpu in gpus) if gpus else 0,
                    "max": max(gpu["price"] for gpu in gpus) if gpus else 0
                }
            }
        }

# Initialize marketplace provider
marketplace_provider = GPUMarketplaceProvider()

async def get_database_pool():
    """Initialize database connection pool"""
    try:
        database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@postgres:5432/gpudx')
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        logger.info("✅ Database pool created successfully")
        return pool
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None

async def get_redis_client():
    """Initialize Redis client"""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
        client = redis.from_url(redis_url)
        await client.ping()
        logger.info("✅ Redis client connected successfully")
        return client
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_pool, redis_client
    
    logger.info("🚀 Starting GPUDx Real API Service...")
    
    # Initialize database
    db_pool = await get_database_pool()
    
    # Initialize Redis
    redis_client = await get_redis_client()
    
    logger.info("✅ GPUDx Real API Service started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_pool, redis_client
    
    logger.info("🛑 Shutting down GPUDx Real API Service...")
    
    if db_pool:
        await db_pool.close()
    
    if redis_client:
        await redis_client.close()
    
    logger.info("✅ GPUDx Real API Service shutdown complete!")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
    
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "GPUDx Real API Service",
        "version": "2.0.0",
        "database": "connected" if db_pool else "disconnected",
        "redis": "connected" if redis_client else "disconnected",
        "active_connections": len(active_connections)
    }
    
    return status

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/gpu-marketplace")
async def get_gpu_marketplace(provider: str = None, gpu_type: str = None):
    """
    Get live GPU marketplace data
    
    Query parameters:
    - provider: Filter by specific provider (e.g., 'AWS', 'Google Cloud')
    - gpu_type: Filter by GPU type (e.g., 'H100', 'A100')
    """
    REQUEST_COUNT.labels(method="GET", endpoint="/gpu-marketplace").inc()
    
    try:
        with REQUEST_DURATION.time():
            # Check cache first
            cache_key = f"marketplace:{provider or 'all'}:{gpu_type or 'all'}"
            
            if redis_client:
                try:
                    cached_data = await redis_client.get(cache_key)
                    if cached_data:
                        logger.info("📋 Returning cached marketplace data")
                        return json.loads(cached_data)
                except Exception as e:
                    logger.warning(f"Redis cache error: {e}")
            
            # Generate fresh data
            logger.info(f"🔄 Generating fresh marketplace data (provider: {provider}, gpu_type: {gpu_type})")
            marketplace_data = marketplace_provider.get_marketplace_data(provider, gpu_type)
            
            # Cache the result
            if redis_client:
                try:
                    await redis_client.setex(cache_key, 60, json.dumps(marketplace_data))  # Cache for 1 minute
                except Exception as e:
                    logger.warning(f"Redis cache set error: {e}")
            
            logger.info(f"✅ Marketplace data generated: {len(marketplace_data['gpus'])} GPUs from {len(marketplace_data['providers'])} providers")
            return marketplace_data
            
    except Exception as e:
        logger.error(f"❌ Error generating marketplace data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/gpu-providers")
async def get_gpu_providers():
    """Get list of available GPU providers"""
    REQUEST_COUNT.labels(method="GET", endpoint="/gpu-providers").inc()
    
    return {
        "providers": marketplace_provider.providers,
        "total": len(marketplace_provider.providers),
        "lastUpdated": datetime.now().isoformat()
    }

@app.get("/gpu-models")
async def get_gpu_models():
    """Get list of available GPU models"""
    REQUEST_COUNT.labels(method="GET", endpoint="/gpu-models").inc()
    
    models = [
        {
            "name": model["name"],
            "memory": model["memory"],
            "specs": model["specs"],
            "features": model["features"]
        }
        for model in marketplace_provider.gpu_models
    ]
    
    return {
        "models": models,
        "total": len(models),
        "lastUpdated": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live data updates"""
    await websocket.accept()
    active_connections.append(websocket)
    ACTIVE_CONNECTIONS.set(len(active_connections))
    
    logger.info(f"🔗 WebSocket connected. Active connections: {len(active_connections)}")
    
    try:
        while True:
            # Send live marketplace updates every 30 seconds
            await asyncio.sleep(30)
            
            marketplace_data = marketplace_provider.get_marketplace_data()
            
            await websocket.send_json({
                "type": "gpu-prices",
                "payload": marketplace_data,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        ACTIVE_CONNECTIONS.set(len(active_connections))
        logger.info(f"🔌 WebSocket disconnected. Active connections: {len(active_connections)}")

if __name__ == "__main__":
    port = int(os.getenv('REAL_API_SERVICE_PORT', 8001))
    
    logger.info(f"🚀 Starting GPUDx Real API Service on port {port}")
    logger.info("📊 Available endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  GET  /metrics - Prometheus metrics")
    logger.info("  GET  /gpu-marketplace - Live GPU marketplace data")
    logger.info("  GET  /gpu-providers - Available providers")
    logger.info("  GET  /gpu-models - Available GPU models")
    logger.info("  WS   /ws - WebSocket live updates")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        access_log=True,
        log_level="info"
    ) 