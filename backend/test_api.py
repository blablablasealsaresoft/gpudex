#!/usr/bin/env python3
"""
Test script for GPUDex API
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

async def test_endpoint(session, endpoint, description):
    """Test a single API endpoint"""
    try:
        print(f"\n🔍 Testing {description}...")
        print(f"   Endpoint: {endpoint}")
        
        async with session.get(f"{API_BASE}{endpoint}") as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Success! Status: {response.status}")
                print(f"   📊 Response: {json.dumps(data, indent=2)[:200]}...")
                return True
            else:
                print(f"   ❌ Failed! Status: {response.status}")
                return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def test_prices_endpoint(session):
    """Test the prices endpoint with different parameters"""
    print(f"\n🔍 Testing prices endpoint...")
    
    test_cases = [
        ("/api/v1/prices?gpu=4090", "RTX 4090 prices"),
        ("/api/v1/prices?gpu=a100&region=us-east", "A100 prices in US East"),
        ("/api/v1/prices?gpu=h100&region=global", "H100 prices globally"),
    ]
    
    for endpoint, description in test_cases:
        try:
            print(f"   Testing {description}...")
            async with session.get(f"{API_BASE}{endpoint}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Success! Found {len(data.get('prices', []))} prices")
                    if data.get('prices'):
                        best_price = data['prices'][0]
                        print(f"   🏆 Best price: ${best_price['price']}/hr from {best_price['provider']}")
                else:
                    print(f"   ❌ Failed! Status: {response.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

async def test_alert_creation(session):
    """Test alert creation"""
    print(f"\n🔍 Testing alert creation...")
    
    alert_data = {
        "email": "test@gpudex.io",
        "gpu_type": "4090",
        "target_price": 0.30
    }
    
    try:
        async with session.post(
            f"{API_BASE}/api/v1/alerts",
            json=alert_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Alert created successfully!")
                print(f"   📧 Alert ID: {data.get('alert_id')}")
                return True
            else:
                print(f"   ❌ Failed! Status: {response.status}")
                return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 GPUDex API Test Suite")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test basic endpoints
        await test_endpoint(session, "/", "Health check")
        await test_endpoint(session, "/api/v1/providers", "Providers list")
        await test_endpoint(session, "/api/v1/analytics", "Analytics")
        
        # Test prices endpoint
        await test_prices_endpoint(session)
        
        # Test alert creation
        await test_alert_creation(session)
        
        # Test price history
        await test_endpoint(session, "/api/v1/history/4090", "Price history for RTX 4090")
        
        # Test provider stats
        await test_endpoint(session, "/api/v1/providers/Vast.ai/stats", "Vast.ai stats")
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed!")

if __name__ == "__main__":
    asyncio.run(main()) 