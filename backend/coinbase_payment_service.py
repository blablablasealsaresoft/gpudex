"""
Coinbase Commerce Payment Service
Handles crypto payments through Coinbase Commerce for Web3 users
"""

import os
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

class CoinbaseCommercePayment(BaseModel):
    amount_usd: float
    wallet_address: str
    wallet_type: str
    order_description: str
    gpu_booking_details: Dict[str, Any]

class CoinbaseCommerceService:
    def __init__(self):
        self.api_key = os.getenv('COINBASE_COMMERCE_API_KEY')
        self.base_url = 'https://api.commerce.coinbase.com'
        self.headers = {
            'Content-Type': 'application/json',
            'X-CC-Api-Key': self.api_key,
            'X-CC-Version': '2018-03-22'
        }
        
        if not self.api_key:
            logger.warning("Coinbase Commerce API key not configured")

    async def create_charge(self, payment_request: CoinbaseCommercePayment) -> Dict[str, Any]:
        """Create a Coinbase Commerce charge for crypto payment"""
        try:
            if not self.api_key:
                return self._create_demo_charge(payment_request)
            
            # Prepare charge data
            charge_data = {
                "name": f"GPU Rental - {len(payment_request.gpu_booking_details.get('items', []))} items",
                "description": payment_request.order_description,
                "pricing_type": "fixed_price",
                "local_price": {
                    "amount": str(payment_request.amount_usd),
                    "currency": "USD"
                },
                "metadata": {
                    "wallet_address": payment_request.wallet_address,
                    "wallet_type": payment_request.wallet_type,
                    "gpu_items": json.dumps(payment_request.gpu_booking_details.get('items', [])),
                    "discount_applied": str(payment_request.gpu_booking_details.get('discount_applied', 0)),
                    "created_at": datetime.now().isoformat()
                },
                "redirect_url": "http://localhost:3000?payment=success",
                "cancel_url": "http://localhost:3000?payment=cancelled"
            }
            
            # Create charge
            response = requests.post(
                f"{self.base_url}/charges",
                headers=self.headers,
                json=charge_data,
                timeout=30
            )
            
            if response.status_code == 201:
                charge = response.json()['data']
                
                # Extract pricing information
                pricing = charge.get('pricing', {})
                
                return {
                    "charge_id": charge['id'],
                    "hosted_url": charge['hosted_url'],
                    "amount_usd": payment_request.amount_usd,
                    "amount_crypto": float(pricing.get('ethereum', {}).get('amount', 0)),
                    "cryptocurrency": "ETH",
                    "expires_at": charge['expires_at'],
                    "status": "pending",
                    "payment_url": charge['hosted_url']
                }
            else:
                logger.error(f"Coinbase Commerce API error: {response.status_code} - {response.text}")
                return self._create_demo_charge(payment_request)
                
        except Exception as e:
            logger.error(f"Error creating Coinbase Commerce charge: {e}")
            return self._create_demo_charge(payment_request)

    def _create_demo_charge(self, payment_request: CoinbaseCommercePayment) -> Dict[str, Any]:
        """Create a demo charge when API key is not available"""
        # Convert USD to approximate ETH (using ~$2000/ETH estimate)
        eth_amount = payment_request.amount_usd / 2000
        
        return {
            "charge_id": f"demo_charge_{datetime.now().timestamp()}",
            "hosted_url": "https://commerce.coinbase.com/demo",
            "amount_usd": payment_request.amount_usd,
            "amount_crypto": eth_amount,
            "cryptocurrency": "ETH",
            "expires_at": (datetime.now().timestamp() + 3600) * 1000,  # 1 hour from now
            "status": "pending",
            "payment_url": "https://commerce.coinbase.com/demo",
            "demo_mode": True
        }

    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """Get the status of a Coinbase Commerce charge"""
        try:
            if not self.api_key or charge_id.startswith('demo_'):
                return {
                    "charge_id": charge_id,
                    "status": "pending",
                    "demo_mode": True
                }
            
            response = requests.get(
                f"{self.base_url}/charges/{charge_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                charge = response.json()['data']
                return {
                    "charge_id": charge['id'],
                    "status": charge['timeline'][-1]['status'] if charge.get('timeline') else 'pending',
                    "payments": charge.get('payments', [])
                }
            else:
                logger.error(f"Error fetching charge status: {response.status_code}")
                return {"charge_id": charge_id, "status": "error"}
                
        except Exception as e:
            logger.error(f"Error getting charge status: {e}")
            return {"charge_id": charge_id, "status": "error"}

    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate Coinbase Commerce webhook signature"""
        try:
            import hmac
            import hashlib
            
            webhook_secret = os.getenv('COINBASE_COMMERCE_WEBHOOK_SECRET')
            if not webhook_secret:
                return False
            
            computed_signature = hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(computed_signature, signature)
            
        except Exception as e:
            logger.error(f"Error validating webhook: {e}")
            return False

# Global service instance
coinbase_commerce_service = CoinbaseCommerceService() 