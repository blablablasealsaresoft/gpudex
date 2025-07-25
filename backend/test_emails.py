#!/usr/bin/env python3
"""
Test script for GPUDex email notification system
"""

import os
import asyncio
import requests
import json
from datetime import datetime

# Test configuration
API_BASE = "http://localhost:8000"
TEST_EMAIL = "test@example.com"  # Change this to your email for testing

async def test_email_system():
    """Test the complete email notification system."""
    
    print("🧪 GPUDex Email System Test")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. 🔍 Testing API Health...")
    try:
        response = requests.get(f"{API_BASE}/")
        if response.status_code == 200:
            print("   ✅ API is running")
        else:
            print(f"   ❌ API health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        return
    
    # Test 2: Create alert (should trigger welcome email)
    print("\n2. 📧 Creating price alert (should send welcome email)...")
    alert_data = {
        "email": TEST_EMAIL,
        "gpu_type": "a100",
        "target_price": 5.0  # High target to test welcome email without triggering price alert
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/v1/alerts", json=alert_data)
        result = response.json()
        
        if response.status_code == 200:
            print(f"   ✅ Alert created successfully")
            print(f"   📧 Welcome email sent: {result.get('welcome_sent', False)}")
            alert_id = result.get('alert_id')
        else:
            print(f"   ❌ Failed to create alert: {result}")
            return
    except Exception as e:
        print(f"   ❌ Error creating alert: {e}")
        return
    
    # Test 3: Create another alert (should NOT send welcome email)
    print("\n3. 📝 Creating second alert (no welcome email expected)...")
    alert_data2 = {
        "email": TEST_EMAIL,
        "gpu_type": "h100",
        "target_price": 8.0
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/v1/alerts", json=alert_data2)
        result = response.json()
        
        if response.status_code == 200:
            print(f"   ✅ Second alert created")
            print(f"   📧 Welcome email sent: {result.get('welcome_sent', False)} (should be False)")
        else:
            print(f"   ❌ Failed to create second alert: {result}")
    except Exception as e:
        print(f"   ❌ Error creating second alert: {e}")
    
    # Test 4: Create low-price alert (should trigger price notification)
    print("\n4. 🎯 Creating low-price alert (should trigger price notification)...")
    alert_data3 = {
        "email": TEST_EMAIL,
        "gpu_type": "a100",
        "target_price": 0.1  # Very low target to trigger notification
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/v1/alerts", json=alert_data3)
        result = response.json()
        
        if response.status_code == 200:
            print(f"   ✅ Low-price alert created")
            print(f"   ⏳ Background service will check this alert in ~5 minutes")
        else:
            print(f"   ❌ Failed to create low-price alert: {result}")
    except Exception as e:
        print(f"   ❌ Error creating low-price alert: {e}")
    
    # Test 5: Check current prices
    print("\n5. 💰 Checking current GPU prices...")
    try:
        response = requests.get(f"{API_BASE}/api/v1/prices?gpu=a100&region=us-east")
        result = response.json()
        
        if response.status_code == 200:
            best_price = result.get('best_price', {})
            print(f"   ✅ Current A100 best price: ${best_price.get('price', 'N/A')}/hr from {best_price.get('provider', 'N/A')}")
            
            if best_price.get('price'):
                if alert_data3['target_price'] >= best_price['price']:
                    print(f"   🎯 Target ${alert_data3['target_price']}/hr >= Current ${best_price['price']}/hr - Alert should trigger!")
                else:
                    print(f"   ⏳ Target ${alert_data3['target_price']}/hr < Current ${best_price['price']}/hr - Alert won't trigger yet")
        else:
            print(f"   ❌ Failed to get prices: {result}")
    except Exception as e:
        print(f"   ❌ Error getting prices: {e}")
    
    # Test 6: Environment check
    print("\n6. 🔧 Checking email configuration...")
    sendgrid_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('FROM_EMAIL', 'alerts@gpudex.com')
    
    if sendgrid_key:
        print(f"   ✅ SendGrid API key configured")
        print(f"   📧 From email: {from_email}")
    else:
        print(f"   ⚠️  SendGrid API key not set - emails will be logged but not sent")
        print(f"   💡 Set SENDGRID_API_KEY environment variable to enable real emails")
    
    print("\n" + "=" * 50)
    print("✅ Email system test completed!")
    print(f"\n📧 If SendGrid is configured, check {TEST_EMAIL} for:")
    print("   • Welcome email (from first alert)")
    print("   • Price alert (if target was met)")
    print("\n⏳ Background alert checker runs every 5 minutes")
    print("📊 Check Docker logs: docker-compose logs backend")

def test_email_templates():
    """Test email template generation without sending."""
    print("\n🎨 Testing email templates...")
    
    from email_service import email_service
    
    # Test alert email HTML
    html = email_service._create_alert_html("a100", 2.0, 1.5, "TensorDock", 0.5)
    print(f"   ✅ Alert email template generated ({len(html)} chars)")
    
    # Test welcome email HTML  
    welcome_html = email_service._create_welcome_html()
    print(f"   ✅ Welcome email template generated ({len(welcome_html)} chars)")
    
    print("   💡 Templates are ready for sending")

if __name__ == "__main__":
    print(f"🕐 Test started at {datetime.now()}")
    
    # Test templates first
    test_email_templates()
    
    # Test full system
    asyncio.run(test_email_system())
    
    print(f"\n🕐 Test completed at {datetime.now()}") 