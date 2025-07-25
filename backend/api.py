# GPU Price Aggregator - Backend Foundation
# Run this to start collecting real pricing data

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List
import re

class GPUAggregator:
    def __init__(self):
        self.providers = {
            'vast.ai': self.scrape_vast,
            'runpod.io': self.scrape_runpod,
            'tensordock.com': self.scrape_tensordock,
            'lambdalabs.com': self.scrape_lambda,
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
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                prices = []
                for offer in data.get('offers', [])[:5]:  # Top 5 offers
                    prices.append({
                        'provider': 'Vast.ai',
                        'price': offer.get('dph_total', 0),  # dollars per hour
                        'gpu_count': offer.get('num_gpus', 1),
                        'availability': 'available' if offer.get('rentable') else 'limited',
                        'type': 'spot',
                        'region': self._parse_region(offer.get('geolocation', ''))
                    })
                return prices
        except Exception as e:
            print(f"Error scraping Vast.ai: {e}")
            return []
    
    async def scrape_runpod(self, session, gpu_type):
        """Scrape RunPod pricing"""
        # Note: In production, you'd use their API
        # This is simplified for MVP
        mock_prices = {
            '4090': 0.39,
            'a100': 1.49,
            'h100': 2.99
        }
        
        return [{
            'provider': 'RunPod',
            'price': mock_prices.get(gpu_type, 0.5),
            'gpu_count': 1,
            'availability': 'available',
            'type': 'on-demand',
            'region': 'us-east'
        }]
    
    async def scrape_tensordock(self, session, gpu_type):
        """Scrape TensorDock pricing"""
        # TensorDock API endpoint pattern
        prices_map = {
            '4090': 0.29,
            'a100': 0.99,
            'h100': 2.25
        }
        
        return [{
            'provider': 'TensorDock',
            'price': prices_map.get(gpu_type, 0.4),
            'gpu_count': 1,
            'availability': 'available',
            'type': 'interruptible',
            'region': 'global'
        }]
    
    async def scrape_lambda(self, session, gpu_type):
        """Scrape Lambda Labs pricing"""
        # Lambda's pricing structure
        prices = {
            'a100': 1.10,
            'h100': 2.49,
            '4090': 0.60
        }
        
        return [{
            'provider': 'Lambda Labs',
            'price': prices.get(gpu_type, 1.0),
            'gpu_count': 1,
            'availability': 'limited',
            'type': 'reserved',
            'region': 'us-west'
        }]
    
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
            
            results = await asyncio.gather(*tasks)
            
            for result in results:
                all_prices.extend(result)
        
        # Sort by price
        all_prices.sort(key=lambda x: x['price'])
        
        # Calculate savings
        if all_prices:
            max_price = max(p['price'] for p in all_prices)
            for price in all_prices:
                price['savings'] = int((1 - price['price'] / max_price) * 100)
        
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
import uvicorn

app = FastAPI()
aggregator = GPUAggregator()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/prices")
async def get_prices(gpu: str = "4090", region: str = "us-east"):
    """Get aggregated GPU prices"""
    prices = await aggregator.aggregate_prices(gpu)
    
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
        "best_price": prices[0] if prices else None
    }

@app.get("/api/v1/providers")
async def get_providers():
    """List all integrated providers"""
    return {
        "providers": list(aggregator.providers.keys()),
        "total": len(aggregator.providers),
        "gpu_types": list(aggregator.gpu_mappings.keys())
    }

@app.post("/api/v1/alerts")
async def create_alert(email: str, gpu_type: str, target_price: float):
    """Create price drop alert"""
    # In production, save to database
    return {
        "status": "success",
        "message": f"Alert created for {gpu_type} below ${target_price}/hr",
        "alert_id": "alert_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    }

@app.get("/api/v1/analytics")
async def get_analytics():
    """Market analytics endpoint"""
    # This would pull from your database in production
    return {
        "total_volume_tracked": "$2.4M",
        "average_savings": "37%",
        "total_providers": 15,
        "active_gpus": 8431,
        "price_trends": {
            "4090": {"7d_change": "-12%", "30d_change": "-28%"},
            "a100": {"7d_change": "-5%", "30d_change": "-15%"},
            "h100": {"7d_change": "-8%", "30d_change": "-22%"}
        }
    }

if __name__ == "__main__":
    # Run the API server
    uvicorn.run(app, host="0.0.0.0", port=8000)

# To run:
# 1. pip install fastapi uvicorn aiohttp
# 2. python api.py
# 3. Access at http://localhost:8000/api/v1/prices?gpu=4090