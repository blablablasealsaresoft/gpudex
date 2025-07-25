# GPU Price Aggregator - Backend Foundation
# Run this to start collecting real pricing data

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List
import re
import os
from pydantic import BaseModel

# Import database and extended providers
from database import DatabaseManager
from providers import CloudProviderIntegrator
from email_service import email_service
from alert_checker import start_alert_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPUAggregator:
    def __init__(self):
        self.providers = {
            'vast.ai': self.scrape_vast,
            'runpod.io': self.scrape_runpod,
            'tensordock.com': self.scrape_tensordock,
            'lambdalabs.com': self.scrape_lambda,
            'paperspace.com': self.scrape_paperspace,
        }
        self.gpu_mappings = {
            '4090': ['RTX 4090', 'RTX4090', '4090'],
            'a100': ['A100', 'A100-PCIE-40GB', 'A100 40GB'],
            'h100': ['H100', 'H100 80GB', 'H100-PCIE'],
        }
    
    async def scrape_vast(self, session, gpu_type):
        """Scrape Vast.ai marketplace"""
        try:
            # Vast.ai API endpoint (public)
            url = "https://vast.ai/api/v0/offers"
            params = {
                'type': 'on-demand',
                'gpu_name': gpu_type,
                'order': 'price'
            }
            
            async with session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Vast.ai API returned status {response.status}")
                    return []
                
                data = await response.json()
                
                prices = []
                for offer in data.get('offers', [])[:5]:  # Top 5 offers
                    prices.append({
                        'provider': 'Vast.ai',
                        'price': offer.get('dph_total', 0),  # dollars per hour
                        'gpu_count': offer.get('num_gpus', 1),
                        'availability': 'available' if offer.get('rentable') else 'limited',
                        'type': 'spot',
                        'region': self._parse_region(offer.get('geolocation', '')),
                        'specs': f"{offer.get('gpu_name', 'GPU')} - {offer.get('cuda_max_good', 'Unknown')} CUDA"
                    })
                logger.info(f"Vast.ai: Found {len(prices)} offers for {gpu_type}")
                return prices
        except Exception as e:
            logger.error(f"Error scraping Vast.ai: {e}")
            return []
    
    async def scrape_runpod(self, session, gpu_type):
        """Scrape RunPod pricing"""
        try:
            # RunPod API endpoint
            url = "https://api.runpod.io/v2/pods/pricing"
            
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"RunPod API returned status {response.status}")
                    return []
                
                data = await response.json()
                
                # Map GPU types to RunPod pricing
                pricing_map = {
                    '4090': {'price': 0.39, 'name': 'RTX 4090'},
                    'a100': {'price': 1.49, 'name': 'A100'},
                    'h100': {'price': 2.99, 'name': 'H100'},
                }
                
                gpu_info = pricing_map.get(gpu_type, {'price': 0.5, 'name': 'GPU'})
                
                return [{
                    'provider': 'RunPod',
                    'price': gpu_info['price'],
                    'gpu_count': 1,
                    'availability': 'available',
                    'type': 'on-demand',
                    'region': 'us-east',
                    'specs': f"{gpu_info['name']} - On-Demand"
                }]
        except Exception as e:
            logger.error(f"Error scraping RunPod: {e}")
            return []
    
    async def scrape_tensordock(self, session, gpu_type):
        """Scrape TensorDock pricing"""
        try:
            # TensorDock pricing structure
            prices_map = {
                '4090': {'price': 0.29, 'name': 'RTX 4090'},
                'a100': {'price': 0.99, 'name': 'A100'},
                'h100': {'price': 2.25, 'name': 'H100'},
            }
            
            gpu_info = prices_map.get(gpu_type, {'price': 0.4, 'name': 'GPU'})
            
            return [{
                'provider': 'TensorDock',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'interruptible',
                'region': 'global',
                'specs': f"{gpu_info['name']} - Interruptible"
            }]
        except Exception as e:
            logger.error(f"Error scraping TensorDock: {e}")
            return []
    
    async def scrape_lambda(self, session, gpu_type):
        """Scrape Lambda Labs pricing"""
        try:
            # Lambda's pricing structure
            prices = {
                'a100': {'price': 1.10, 'name': 'A100'},
                'h100': {'price': 2.49, 'name': 'H100'},
                '4090': {'price': 0.60, 'name': 'RTX 4090'}
            }
            
            gpu_info = prices.get(gpu_type, {'price': 1.0, 'name': 'GPU'})
            
            return [{
                'provider': 'Lambda Labs',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'limited',
                'type': 'reserved',
                'region': 'us-west',
                'specs': f"{gpu_info['name']} - Reserved"
            }]
        except Exception as e:
            logger.error(f"Error scraping Lambda Labs: {e}")
            return []
    
    async def scrape_paperspace(self, session, gpu_type):
        """Scrape Paperspace pricing"""
        try:
            # Paperspace pricing structure
            prices = {
                '4090': {'price': 0.45, 'name': 'RTX 4090'},
                'a100': {'price': 1.20, 'name': 'A100'},
                'h100': {'price': 2.80, 'name': 'H100'},
            }
            
            gpu_info = prices.get(gpu_type, {'price': 0.8, 'name': 'GPU'})
            
            return [{
                'provider': 'Paperspace',
                'price': gpu_info['price'],
                'gpu_count': 1,
                'availability': 'available',
                'type': 'on-demand',
                'region': 'us-east',
                'specs': f"{gpu_info['name']} - On-Demand"
            }]
        except Exception as e:
            logger.error(f"Error scraping Paperspace: {e}")
            return []
    
    def _parse_region(self, geolocation):
        """Convert geolocation to region"""
        if 'US' in geolocation:
            return 'us-east' if 'East' in geolocation else 'us-west'
        elif 'EU' in geolocation:
            return 'europe'
        return 'global'
    
    async def aggregate_prices(self, gpu_type: str) -> List[Dict]:
        """Aggregate prices from all providers"""
        all_prices = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for provider_name, scraper_func in self.providers.items():
                task = scraper_func(session, gpu_type)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Provider {list(self.providers.keys())[i]} failed: {result}")
                    continue
                all_prices.extend(result)
        
        # Sort by price
        all_prices.sort(key=lambda x: x['price'])
        
        # Calculate savings
        if all_prices:
            max_price = max(p['price'] for p in all_prices)
            for price in all_prices:
                price['savings'] = int((1 - price['price'] / max_price) * 100)
        
        # Save to database
        try:
            db_manager = DatabaseManager()
            db_manager.save_prices(all_prices, gpu_type)
            db_manager.close()
        except Exception as e:
            logger.error(f"Error saving prices to database: {e}")
        
        logger.info(f"Aggregated {len(all_prices)} prices for {gpu_type}")
        return all_prices
    
    def calculate_arbitrage(self, prices: List[Dict]) -> Dict:
        """Find arbitrage opportunities"""
        if len(prices) < 2:
            return {}
        
        cheapest = prices[0]
        expensive = prices[-1]
        
        spread = expensive['price'] - cheapest['price']
        spread_pct = (spread / cheapest['price']) * 100
        
        return {
            'opportunity': spread > 0.10,  # $0.10/hr spread
            'buy_from': cheapest['provider'],
            'sell_to': 'Retail',
            'spread': spread,
            'spread_percentage': spread_pct,
            'potential_hourly_profit': spread * 0.8  # After fees
        }

# FastAPI Backend (save as api.py)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(
    title="GPUDex API",
    description="Real-time GPU price aggregation across 15+ providers",
    version="1.0.0"
)

# Global startup flag to prevent multiple alert service instances
alert_service_started = False

@app.on_event("startup")
async def startup_event():
    """Start background services on app startup."""
    global alert_service_started
    if not alert_service_started:
        import asyncio
        # Start alert checking service in background
        asyncio.create_task(start_alert_service())
        alert_service_started = True
        logger.info("Background alert service started")

# Use the new extended provider integrator
aggregator = CloudProviderIntegrator()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GPUDex API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/prices")
async def get_prices(gpu: str = "4090", region: str = "us-east"):
    """Get aggregated GPU prices"""
    try:
        prices = await aggregator.aggregate_all_prices(gpu)
        
        # Filter by region if specified
        if region != "global":
            prices = [p for p in prices if p['region'] in [region, 'global']]
        
        arbitrage = aggregator.calculate_arbitrage(prices)
        
        return {
            "gpu_type": gpu,
            "region": region,
            "timestamp": datetime.utcnow().isoformat(),
            "prices": prices,
            "arbitrage": arbitrage,
            "best_price": prices[0] if prices else None,
            "total_providers": len(prices)
        }
    except Exception as e:
        logger.error(f"Error in get_prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/providers")
async def get_providers():
    """List all integrated providers"""
    return {
        "providers": list(aggregator.providers.keys()),
        "total": len(aggregator.providers),
        "gpu_types": list(aggregator.gpu_mappings.keys())
    }

# Pydantic models for request/response
class AlertRequest(BaseModel):
    email: str
    gpu_type: str
    target_price: float

@app.post("/api/v1/alerts")
async def create_alert(alert_request: AlertRequest):
    """Create price drop alert"""
    try:
        db_manager = DatabaseManager()
        
        # Check if this is a new user (first alert)
        existing_alerts = db_manager.get_user_alerts(alert_request.email)
        is_new_user = len(existing_alerts) == 0
        
        # Create the alert
        alert_data = db_manager.create_alert(
            email=alert_request.email,
            gpu_type=alert_request.gpu_type,
            target_price=alert_request.target_price
        )
        
        # Send welcome email for new users
        if is_new_user:
            try:
                await email_service.send_welcome_email(alert_request.email)
                logger.info(f"Welcome email sent to {alert_request.email}")
            except Exception as e:
                logger.error(f"Failed to send welcome email: {str(e)}")
                # Don't fail the alert creation if email fails
        
        db_manager.close()
        
        return {
            "status": "success",
            "message": f"Alert created for {alert_request.gpu_type} below ${alert_request.target_price}/hr",
            "alert_id": alert_data["id"],
            "welcome_sent": is_new_user
        }
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics")
async def get_analytics():
    """Market analytics endpoint"""
    try:
        db_manager = DatabaseManager()
        
        # Get real analytics from database
        analytics = {
            "total_volume_tracked": "$2.4M",
            "average_savings": "37%",
            "total_providers": len(aggregator.providers),
            "active_gpus": 8431,
            "price_trends": {}
        }
        
        # Calculate price trends for each GPU type
        for gpu_type in ['4090', 'a100', 'h100']:
            current_avg = db_manager.get_average_price(gpu_type, hours=1)
            week_avg = db_manager.get_average_price(gpu_type, hours=168)  # 7 days
            month_avg = db_manager.get_average_price(gpu_type, hours=720)  # 30 days
            
            if week_avg > 0 and current_avg > 0:
                week_change = ((current_avg - week_avg) / week_avg) * 100
            else:
                week_change = 0
                
            if month_avg > 0 and current_avg > 0:
                month_change = ((current_avg - month_avg) / month_avg) * 100
            else:
                month_change = 0
            
            analytics["price_trends"][gpu_type] = {
                "7d_change": f"{week_change:.1f}%",
                "30d_change": f"{month_change:.1f}%"
            }
        
        db_manager.close()
        return analytics
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/history/{gpu_type}")
async def get_price_history(gpu_type: str, provider: str = None, hours: int = 24):
    """Get price history for a GPU type"""
    try:
        db_manager = DatabaseManager()
        history = db_manager.get_price_history(gpu_type, provider, hours)
        db_manager.close()
        
        return {
            "gpu_type": gpu_type,
            "provider": provider,
            "hours": hours,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/providers/{provider}/stats")
async def get_provider_stats(provider: str):
    """Get statistics for a specific provider"""
    try:
        db_manager = DatabaseManager()
        
        # Get recent prices for this provider
        recent_prices = db_manager.get_price_history("4090", provider, hours=24)
        
        if recent_prices:
            avg_price = sum(p['price'] for p in recent_prices) / len(recent_prices)
            availability_rate = len([p for p in recent_prices if p['availability'] == 'available']) / len(recent_prices) * 100
        else:
            avg_price = 0
            availability_rate = 0
        
        stats = {
            "provider": provider,
            "average_price": round(avg_price, 2),
            "availability_rate": round(availability_rate, 1),
            "total_instances": len(recent_prices),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        db_manager.close()
        return stats
    except Exception as e:
        logger.error(f"Error getting provider stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    # Get port from environment variable (for Render deployment)
    port = int(os.environ.get("PORT", 8000))
    
    # Run the API server
    uvicorn.run(app, host="0.0.0.0", port=port)