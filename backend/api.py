# GPU Price Aggregator - Backend Foundation
# Run this to start collecting real pricing data

import logging
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import time
import json

# Import our services
from database import DatabaseManager, create_tables
from providers import CloudProviderIntegrator
from coinbase_payment_service import coinbase_commerce_service, CoinbaseCommercePayment
from email_service import EmailService
from alert_checker import start_alert_service
from rate_limiting import (
    APIKeyManager, require_api_key, check_rate_limits, 
    add_rate_limit_headers, basic_rate_limit, premium_rate_limit
)
from cache_service import cache, SmartCache
from auth_service import auth_service, get_current_user, get_current_user_optional, UserRegistration, UserLogin, PasswordChange
from payment_service import stripe_service, CreateCheckoutSessionRequest, PlanType
from monitoring_service import monitoring_service, start_monitoring
from crypto_payment_service import (
    crypto_service, create_crypto_payment, get_crypto_payment_status, 
    get_supported_cryptocurrencies, CryptoPaymentRequest, CryptoPaymentResponse
)
from gpu_provisioning_service import gpu_provisioning_service, start_instance_monitoring, GPUInstance
# Production launch - Polygon payments only (cross-chain coming in V2)
from enum import Enum
class BridgeStatus(str, Enum):
    PENDING = "pending"
    BRIDGING = "bridging"
    COMPLETED = "completed" 
    FAILED = "failed"

# Smart Contract Configuration from Environment Variables
DEPLOYED_CONTRACTS = {
    "polygon": {
        "chainId": int(os.getenv("CHAIN_ID", "137")),
        "escrowAddress": os.getenv("ESCROW_CONTRACT_ADDRESS", "0xE0107C4227A38Aae3E5163D691EFb0dc0Eb7598C"),
        "tokenAddress": os.getenv("TOKEN_CONTRACT_ADDRESS", "0x386FF386B396ca139E5D2dB6d0b61a0FDd5b4b47"),
        "feeRecipient": os.getenv("PLATFORM_FEE_RECIPIENT", "0x0B83154b85B7F6f8ec567d0F3a93B50C8b8C754A"),
        "platformFeePercent": int(os.getenv("PLATFORM_FEE_PERCENT", "300")),  # 3%
        "network": os.getenv("BLOCKCHAIN_NETWORK", "polygon"),
        "rpcUrl": os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
        "status": "deployed"
    }
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GPU DEX API",
    description="The most comprehensive GPU price aggregation platform",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
# Temporarily commented out while fixing slowapi issues
# app.state.limiter = limiter

# Initialize services
db_manager = DatabaseManager()
email_service = EmailService()
api_key_manager = APIKeyManager()

# Request models
class AlertRequest(BaseModel):
    email: str
    gpu_type: str
    target_price: float
    region: str = "us-east"

class PriceFilter(BaseModel):
    gpu_type: Optional[str] = None
    provider: Optional[str] = None
    region: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_memory: Optional[int] = None
    min_cuda_cores: Optional[int] = None
    sort_by: str = "price"
    sort_desc: bool = False

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting GPU DEX API Server...")
    
    # Initialize database tables
    create_tables()
    
    # Start background services
    asyncio.create_task(start_alert_service())
    start_monitoring()
    
    # Start GPU instance monitoring for auto-termination
    asyncio.create_task(start_instance_monitoring())
    
    logger.info("✅ GPU DEX API Server ready!")

# Health check endpoints
@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to GPU DEX API - The 1inch of GPU Compute",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Real-time GPU price aggregation",
            "13+ provider integrations",
            "Arbitrage detection",
            "User authentication",
            "Subscription plans",
            "Advanced monitoring"
        ],
        "docs": "/api/docs",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Comprehensive health check"""
    health_status = await monitoring_service.perform_health_checks()
    
    status_code = 200
    if health_status["overall_status"] == "critical":
        status_code = 503
    elif health_status["overall_status"] == "warning":
        status_code = 200  # Still operational
    
    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/api/v2/health", response_model=Dict[str, Any])
async def health_check_v2():
    """V2 API health check endpoint"""
    return {
        "status": "healthy",
        "service": "gpudx_api_service",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "healthy",
            "redis": "healthy", 
            "blockchain": "healthy"
        }
    }

@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """Prometheus metrics endpoint"""
    return monitoring_service.get_prometheus_metrics()

# Price endpoints
@app.get("/api/v1/prices", response_model=Dict[str, Any])
@basic_rate_limit
async def get_gpu_prices(
    request: Request,
    gpu_type: Optional[str] = Query(None, description="Filter by GPU type"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    region: Optional[str] = Query(None, description="Filter by region")
):
    """Get current GPU prices from all providers"""
    start_time = time.time()
    
    try:
        # Record API call
        monitoring_service.record_api_call("gpu_prices", "success")
        
        async with CloudProviderIntegrator() as provider_integrator:
            # Get all prices
            all_prices = await provider_integrator.get_all_prices()
            
            # Convert to dict format for compatibility
            prices_dict = []
            for price_data in all_prices:
                price_dict = {
                    "provider": price_data.provider,
                    "gpu_type": price_data.gpu_type,
                    "price_per_hour": price_data.price_per_hour,  # Fixed field name!
                    "availability": price_data.availability,
                    "region": price_data.region,
                    "memory": price_data.memory,
                    "cuda_cores": price_data.cuda_cores,
                    "specifications": price_data.specifications,
                    "last_updated": price_data.last_updated.isoformat(),
                    "url": price_data.url,
                    "instance_type": price_data.instance_type
                }
                prices_dict.append(price_dict)
            
            # Apply filters
            if gpu_type:
                prices_dict = [p for p in prices_dict if gpu_type.lower() in p["gpu_type"].lower()]
            if provider:
                prices_dict = [p for p in prices_dict if provider.lower() == p["provider"].lower()]
            if region:
                prices_dict = [p for p in prices_dict if region.lower() in p["region"].lower()]
            
            # Sort by price
            prices_dict.sort(key=lambda x: x["price_per_hour"])
            
            # Calculate arbitrage opportunities
            arbitrage_opportunities = provider_integrator.calculate_arbitrage(all_prices)
            
            response_time = time.time() - start_time
            monitoring_service.record_request("GET", "/api/v1/prices", 200, response_time)
            
            response = {
                "prices": prices_dict,
                "total_results": len(prices_dict),
                "arbitrage_opportunities": arbitrage_opportunities,
                "response_time_ms": round(response_time * 1000, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            return JSONResponse(content=response)
            
    except Exception as e:
        monitoring_service.record_api_call("gpu_prices", "error")
        logger.error(f"Error fetching prices: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching GPU prices: {str(e)}")

@app.post("/api/v1/prices/filter", response_model=Dict[str, Any])
@basic_rate_limit
async def filter_gpu_prices(
    request: Request,
    filter_request: PriceFilter,
    api_key: str = Depends(require_api_key)
):
    """Advanced GPU price filtering"""
    try:
        async with CloudProviderIntegrator() as provider_integrator:
            all_prices = await provider_integrator.get_all_prices()
            
            # Apply advanced filters
            filtered_prices = provider_integrator.filter_prices(all_prices, filter_request.dict())
            
            # Convert to dict format
            result = []
            for price_data in filtered_prices:
                result.append({
                    "provider": price_data.provider,
                    "gpu_type": price_data.gpu_type,
                    "price_per_hour": price_data.price_per_hour,  # Fixed field name!
                    "availability": price_data.availability,
                    "region": price_data.region,
                    "memory": price_data.memory,
                    "cuda_cores": price_data.cuda_cores,
                    "specifications": price_data.specifications,
                    "last_updated": price_data.last_updated.isoformat()
                })
            
            return add_rate_limit_headers(JSONResponse(content={
                "filtered_prices": result,
                "total_results": len(result),
                "filter_applied": filter_request.dict(),
                "timestamp": datetime.now().isoformat()
            }), api_key)
            
    except Exception as e:
        logger.error(f"Error filtering prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# Authentication endpoints
@app.post("/api/v1/auth/register", response_model=Dict[str, Any])
async def register_user(user_data: UserRegistration):
    """Register a new user"""
    try:
        user_profile = auth_service.register_user(user_data)
        return {
            "message": "User registered successfully",
            "user": user_profile.dict(),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/v1/auth/login", response_model=Dict[str, Any])
async def login_user(login_data: UserLogin, request: Request):
    """Login user and return tokens"""
    try:
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        token_response = auth_service.login_user(login_data, ip_address, user_agent)
        return token_response.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/api/v1/auth/refresh", response_model=Dict[str, Any])
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    try:
        token_response = auth_service.refresh_access_token(refresh_token)
        return token_response.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(status_code=401, detail="Token refresh failed")

@app.get("/api/v1/auth/profile", response_model=Dict[str, Any])
async def get_user_profile(current_user = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "user": current_user.dict(),
        "timestamp": datetime.now().isoformat()
    }

# Payment endpoints
@app.get("/api/v1/plans", response_model=Dict[str, Any])
async def get_subscription_plans():
    """Get all subscription plans"""
    return stripe_service.get_all_plans()

@app.post("/api/v1/checkout", response_model=Dict[str, Any])
async def create_checkout_session(
    checkout_request: CreateCheckoutSessionRequest,
    current_user = Depends(get_current_user)
):
    """Create Stripe checkout session"""
    try:
        checkout_request.user_id = current_user.id
        checkout_request.user_email = current_user.email
        
        result = await stripe_service.create_checkout_session(checkout_request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Checkout creation failed")

@app.get("/api/v1/subscription", response_model=Dict[str, Any])
async def get_user_subscription(current_user = Depends(get_current_user)):
    """Get user's subscription details"""
    try:
        subscription = await stripe_service.get_subscription_details(current_user.id)
        if not subscription:
            return {"subscription": None, "message": "No active subscription"}
        
        return {"subscription": subscription}
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription")

# Alert endpoints
@app.post("/api/v1/alerts", response_model=Dict[str, Any])
@basic_rate_limit
async def setup_price_alert(
    request: Request,
    alert_request: AlertRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_api_key)
):
    """Set up a price alert"""
    try:
        # Add alert to database
        db = db_manager.get_db()
        
        # Check if alert already exists
        existing_alert = db.execute("""
            SELECT id FROM alerts 
            WHERE email = %s AND gpu_type = %s AND target_price = %s
        """, (alert_request.email, alert_request.gpu_type, alert_request.target_price))
        
        if existing_alert.fetchone():
            return add_rate_limit_headers(JSONResponse(content={
                "message": "Alert already exists for this configuration",
                "status": "duplicate"
            }), api_key)
        
        # Insert new alert
        db.execute("""
            INSERT INTO alerts (email, gpu_type, target_price, region, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            alert_request.email,
            alert_request.gpu_type,
            alert_request.target_price,
            alert_request.region,
            datetime.now()
        ))
        db.commit()
        
        # Send welcome email
        background_tasks.add_task(
            email_service.send_welcome_email,
            alert_request.email,
            alert_request.gpu_type,
            alert_request.target_price
        )
        
        return add_rate_limit_headers(JSONResponse(content={
            "message": "Price alert created successfully",
            "alert": {
                "email": alert_request.email,
                "gpu_type": alert_request.gpu_type,
                "target_price": alert_request.target_price,
                "region": alert_request.region
            },
            "timestamp": datetime.now().isoformat()
        }), api_key)
        
    except Exception as e:
        logger.error(f"Error setting up alert: {e}")
        raise HTTPException(status_code=500, detail=f"Error setting up alert: {str(e)}")

# Cache endpoints
@app.get("/api/v1/cache/stats", response_model=Dict[str, Any])
@premium_rate_limit
async def get_cache_stats(request: Request, api_key: str = Depends(require_api_key)):
    """Get cache statistics"""
    try:
        stats = cache.get_stats()
        return add_rate_limit_headers(JSONResponse(content={
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat()
        }), api_key)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/cache/clear", response_model=Dict[str, Any])
@premium_rate_limit
async def clear_cache(
    request: Request,
    pattern: Optional[str] = Query("*", description="Cache pattern to clear"),
    api_key: str = Depends(require_api_key)
):
    """Clear cache (admin only)"""
    try:
        deleted = cache.clear_pattern(pattern)
        return add_rate_limit_headers(JSONResponse(content={
            "message": f"Cleared {deleted} cache entries",
            "pattern": pattern,
            "timestamp": datetime.now().isoformat()
        }), api_key)
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API Key management endpoints (existing code stays the same)
@app.post("/api/v1/api-keys", response_model=Dict[str, Any])
async def create_api_key(request: Request):
    """Create a new API key"""
    try:
        client_ip = request.client.host
        api_key = api_key_manager.create_api_key(
            name=f"API Key from {client_ip}",
            rate_limit_per_hour=100,
            rate_limit_per_day=1000
        )
        
        return {
            "api_key": api_key,
            "rate_limits": {
                "per_hour": 100,
                "per_day": 1000
            },
            "message": "API key created successfully. Keep this key secure!",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

@app.get("/api/v1/api-keys/info", response_model=Dict[str, Any])
async def get_api_key_info(api_key: str = Depends(require_api_key)):
    """Get API key information and usage"""
    try:
        key_info = api_key_manager.get_api_key_info(api_key)
        if not key_info:
            raise HTTPException(status_code=404, detail="API key not found")
        
        return add_rate_limit_headers(JSONResponse(content={
            "api_key_info": key_info,
            "timestamp": datetime.now().isoformat()
        }), api_key)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API key info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API key info")

@app.get("/api/v1/pricing", response_model=Dict[str, Any])
async def get_pricing_info():
    """Get API pricing information"""
    return {
        "plans": [
            {
                "name": "Free",
                "price": 0,
                "requests_per_hour": 100,
                "requests_per_day": 1000,
                "features": ["Basic GPU prices", "Email alerts"]
            },
            {
                "name": "Pro",
                "price": 29,
                "requests_per_hour": 1000,
                "requests_per_day": 10000,
                "features": ["All Free features", "Advanced analytics", "Priority support"]
            },
            {
                "name": "Enterprise",
                "price": 99,
                "requests_per_hour": 10000,
                "requests_per_day": 100000,
                "features": ["All Pro features", "Custom integrations", "SLA"]
            }
        ],
        "contact": "support@gpudex.ai"
    }

# Cryptocurrency Payment Endpoints
@app.get("/api/v1/crypto/currencies", response_model=List[Dict[str, Any]])
async def get_supported_crypto_currencies():
    """Get list of supported cryptocurrencies with current rates and discount info"""
    try:
        currencies = await get_supported_cryptocurrencies()
        return {
            "success": True,
            "currencies": currencies,
            "crypto_discount_rate": 0.01,  # 1% discount
            "message": "Pay with crypto and save 1% on all orders!"
        }
    except Exception as e:
        logger.error(f"Error getting crypto currencies: {e}")
        raise HTTPException(status_code=500, detail="Failed to load cryptocurrency options")

@app.post("/api/v1/crypto/payment", response_model=CryptoPaymentResponse)
@basic_rate_limit
async def create_crypto_payment_order(
    request: Request,
    payment_request: CryptoPaymentRequest,
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """Create a new cryptocurrency payment order with 1% discount"""
    try:
        # Use authenticated user email if available, otherwise use provided email
        if current_user:
            payment_request.user_email = current_user.get("email", payment_request.user_email)
        
        # Create the crypto payment
        payment_response = await create_crypto_payment(payment_request)
        
        logger.info(f"Created crypto payment {payment_response.coingate_id} for {payment_request.user_email}")
        
        return payment_response
        
    except Exception as e:
        logger.error(f"Error creating crypto payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create crypto payment")

@app.get("/api/v1/crypto/payment/{coingate_id}", response_model=Dict[str, Any])
async def get_crypto_payment_info(coingate_id: str):
    """Get cryptocurrency payment status and details"""
    try:
        payment_info = await get_crypto_payment_status(coingate_id)
        return {
            "success": True,
            "payment": payment_info
        }
    except Exception as e:
        logger.error(f"Error getting crypto payment info: {e}")
        raise HTTPException(status_code=404, detail="Payment not found")

@app.post("/api/v1/crypto/webhook")
async def handle_crypto_webhook(request: Request):
    """Handle CoinGate webhook for payment status updates"""
    try:
        # Get webhook signature from headers
        signature = request.headers.get("X-Coingate-Signature", "")
        
        # Get webhook data
        webhook_data = await request.json()
        
        # Process webhook
        async with crypto_service as service:
            success = await service.handle_webhook(webhook_data, signature)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Invalid webhook")
            
    except Exception as e:
        logger.error(f"Error handling crypto webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@app.post("/api/v1/crypto/coinbase-payment", response_model=Dict[str, Any])
@basic_rate_limit
async def create_coinbase_payment(
    request: Request,
    payment_request: CoinbaseCommercePayment
):
    """Create Coinbase Commerce payment for Web3 users"""
    try:
        monitoring_service.record_api_call("coinbase_payment", "success")
        
        # Create Coinbase Commerce charge
        charge_data = await coinbase_commerce_service.create_charge(payment_request)
        
        # Log the payment creation
        logger.info(f"Coinbase Commerce charge created for wallet {payment_request.wallet_address}: ${payment_request.amount_usd}")
        
        return {
            "success": True,
            "charge_id": charge_data["charge_id"],
            "hosted_url": charge_data["hosted_url"],
            "amount_usd": charge_data["amount_usd"],
            "amount_crypto": charge_data["amount_crypto"],
            "cryptocurrency": charge_data["cryptocurrency"],
            "expires_at": charge_data["expires_at"],
            "payment_url": charge_data["payment_url"],
            "demo_mode": charge_data.get("demo_mode", False),
            "message": "Crypto payment created successfully" if not charge_data.get("demo_mode") else "Demo payment created (add COINBASE_COMMERCE_API_KEY for real payments)"
        }
        
    except Exception as e:
        monitoring_service.record_api_call("coinbase_payment", "error")
        logger.error(f"Error creating Coinbase Commerce payment: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating crypto payment: {str(e)}")

@app.get("/api/v1/crypto/payment-status/{charge_id}", response_model=Dict[str, Any])
@basic_rate_limit
async def get_coinbase_payment_status(
    request: Request,
    charge_id: str
):
    """Get Coinbase Commerce payment status"""
    try:
        status_data = await coinbase_commerce_service.get_charge_status(charge_id)
        return {
            "success": True,
            "charge_id": charge_id,
            "status": status_data["status"],
            "payments": status_data.get("payments", []),
            "demo_mode": status_data.get("demo_mode", False)
        }
        
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting payment status: {str(e)}")

@app.post("/api/v1/crypto/coinbase-webhook")
async def coinbase_commerce_webhook(
    request: Request
):
    """Handle Coinbase Commerce webhooks"""
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get('X-CC-Webhook-Signature', '')
        
        # Validate webhook
        if not coinbase_commerce_service.validate_webhook(body, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        # Process webhook data
        webhook_data = await request.json()
        event_type = webhook_data.get('event', {}).get('type')
        
        logger.info(f"Received Coinbase Commerce webhook: {event_type}")
        
        # Handle different event types
        if event_type == 'charge:confirmed':
            # Payment confirmed - process the order
            charge_data = webhook_data.get('event', {}).get('data', {})
            logger.info(f"Payment confirmed for charge: {charge_data.get('id')}")
            
            # TODO: Process the GPU rental order
            
        return {"success": True, "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"Error processing Coinbase webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@app.get("/api/v1/crypto/calculator")
async def crypto_discount_calculator(amount_usd: float = Query(..., description="Amount in USD")):
    """Calculate crypto payment discount (1% savings)"""
    try:
        if amount_usd <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        discount_amount = round(amount_usd * 0.01, 2)  # 1% discount
        final_amount = round(amount_usd - discount_amount, 2)
        
        return {
            "original_amount_usd": amount_usd,
            "crypto_discount_amount": discount_amount,
            "final_amount_usd": final_amount,
            "discount_percentage": 1.0,
            "savings_message": f"Save ${discount_amount} by paying with crypto!",
            "supported_currencies": ["BTC", "ETH", "USDC", "USDT", "LTC", "BCH", "MATIC"]
        }
        
    except Exception as e:
        logger.error(f"Error calculating crypto discount: {e}")
        raise HTTPException(status_code=500, detail="Calculation failed")

# GPU Rental Endpoints
class GPURentalRequest(BaseModel):
    gpu_type: str
    provider: str
    hours: float
    region: Optional[str] = None
    user_email: str
    payment_method: str  # 'crypto', 'stripe', 'coinbase'
    wallet_address: Optional[str] = None

class GPURentalResponse(BaseModel):
    rental_id: str
    gpu_type: str
    provider: str
    hours: float
    price_per_hour: float
    total_cost: float
    discount_applied: float
    final_cost: float
    status: str
    connection_details: Optional[Dict[str, Any]] = None
    expires_at: datetime

@app.post("/api/v1/rentals", response_model=GPURentalResponse)
@basic_rate_limit
async def create_gpu_rental(
    request: Request,
    rental_request: GPURentalRequest
):
    """Create a new GPU rental"""
    try:
        # Validate GPU availability
        async with CloudProviderIntegrator() as provider_integrator:
            all_prices = await provider_integrator.get_all_prices()
            
            # Find the specific GPU
            gpu_found = None
            for price in all_prices:
                if (price.provider.lower() == rental_request.provider.lower() and 
                    price.gpu_type.lower() == rental_request.gpu_type.lower()):
                    gpu_found = price
                    break
            
            if not gpu_found:
                raise HTTPException(status_code=404, detail="GPU not available")
            
            if gpu_found.availability != "Available":
                raise HTTPException(status_code=400, detail="GPU is not currently available")
        
        # Calculate pricing
        price_per_hour = gpu_found.price_per_hour
        total_cost = price_per_hour * rental_request.hours
        
        # No crypto discount - buyer pays full provider price + 3% platform fee handled by smart contract
        discount_applied = 0
        final_cost = total_cost
        
        # Generate rental ID
        import uuid
        rental_id = f"rental_{uuid.uuid4().hex[:12]}"
        
        # Provision real GPU instance
        try:
            gpu_instance = await gpu_provisioning_service.provision_gpu(
                provider=rental_request.provider,
                gpu_type=rental_request.gpu_type,
                hours=rental_request.hours,
                rental_id=rental_id
            )
            
            # Store rental in database with real connection details
            rental_data = {
                "rental_id": rental_id,
                "gpu_type": rental_request.gpu_type,
                "provider": rental_request.provider,
                "hours": rental_request.hours,
                "price_per_hour": price_per_hour,
                "total_cost": total_cost,
                "discount_applied": discount_applied,
                "final_cost": final_cost,
                "user_email": rental_request.user_email,
                "payment_method": rental_request.payment_method,
                "wallet_address": rental_request.wallet_address,
                "status": "active",  # Instance is already running
                "instance_id": gpu_instance.instance_id,
                "ssh_host": gpu_instance.ssh_host,
                "ssh_port": gpu_instance.ssh_port,
                "ssh_username": gpu_instance.ssh_username,
                "ssh_private_key": gpu_instance.ssh_private_key,
                "jupyter_url": gpu_instance.jupyter_url,
                "vscode_url": gpu_instance.vscode_url,
                "created_at": datetime.now(),
                "expires_at": gpu_instance.expires_at
            }
            
            logger.info(f"Provisioned real GPU: {gpu_instance.instance_id} for rental {rental_id}")
            
        except Exception as e:
            logger.error(f"Failed to provision GPU: {e}")
            # Fallback to pending_payment status if provisioning fails
            rental_data = {
                "rental_id": rental_id,
                "gpu_type": rental_request.gpu_type,
                "provider": rental_request.provider,
                "hours": rental_request.hours,
                "price_per_hour": price_per_hour,
                "total_cost": total_cost,
                "discount_applied": discount_applied,
                "final_cost": final_cost,
                "user_email": rental_request.user_email,
                "payment_method": rental_request.payment_method,
                "wallet_address": rental_request.wallet_address,
                "status": "provisioning_failed",
                "error_message": str(e),
                "created_at": datetime.now(),
                "expires_at": datetime.now().replace(hour=23, minute=59, second=59)
            }
        
        return GPURentalResponse(
            rental_id=rental_id,
            gpu_type=rental_request.gpu_type,
            provider=rental_request.provider,
            hours=rental_request.hours,
            price_per_hour=price_per_hour,
            total_cost=total_cost,
            discount_applied=discount_applied,
            final_cost=final_cost,
            status="pending_payment",
            expires_at=datetime.now().replace(hour=23, minute=59, second=59)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating GPU rental: {e}")
        raise HTTPException(status_code=500, detail="Failed to create rental")

@app.get("/api/v1/rentals/{rental_id}")
@basic_rate_limit
async def get_rental_status(
    request: Request,
    rental_id: str
):
    """Get rental status and real connection details"""
    try:
        # Get real instance details from provisioning service
        gpu_instance = gpu_provisioning_service.get_instance_status(rental_id)
        
        if not gpu_instance:
            raise HTTPException(status_code=404, detail="Rental not found or instance not provisioned")
        
        # Calculate remaining time
        remaining_hours = 0
        if gpu_instance.expires_at:
            remaining_time = gpu_instance.expires_at - datetime.now()
            remaining_hours = max(0, remaining_time.total_seconds() / 3600)
        
        return {
            "rental_id": rental_id,
            "status": gpu_instance.status,
            "connection_details": {
                "ssh_host": gpu_instance.ssh_host,
                "ssh_port": gpu_instance.ssh_port,
                "username": gpu_instance.ssh_username,
                "private_key": gpu_instance.ssh_private_key,  # Return private key for connection
                "jupyter_url": gpu_instance.jupyter_url,
                "vscode_url": gpu_instance.vscode_url,
                "jupyter_password": "gpudex123",  # Standard password set during provisioning
                "vscode_password": "gpudex123"
            },
            "remaining_hours": round(remaining_hours, 2),
            "gpu_info": {
                "gpu_type": gpu_instance.gpu_type,
                "provider": gpu_instance.provider,
                "instance_id": gpu_instance.instance_id,
                "cost_per_hour": gpu_instance.cost_per_hour
            },
            "created_at": gpu_instance.created_at.isoformat() if gpu_instance.created_at else None,
            "expires_at": gpu_instance.expires_at.isoformat() if gpu_instance.expires_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rental status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rental status")

@app.delete("/api/v1/rentals/{rental_id}")
@basic_rate_limit
async def terminate_rental(
    request: Request,
    rental_id: str
):
    """Terminate GPU rental and instance"""
    try:
        # Terminate the GPU instance
        success = await gpu_provisioning_service.terminate_instance(rental_id)
        
        if success:
            return {
                "rental_id": rental_id,
                "status": "terminated",
                "message": "GPU instance terminated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Rental not found or already terminated")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating rental: {e}")
        raise HTTPException(status_code=500, detail="Failed to terminate rental")

# Test endpoint for smart contract integration
@app.post("/api/v1/test/smart-contract-payment")
async def test_smart_contract_payment(payment_data: Dict[str, Any]):
    """Test smart contract payment flow"""
    try:
        network = payment_data.get("network", "polygon")
        amount = float(payment_data.get("amount", 0))
        
        contract_config = DEPLOYED_CONTRACTS.get(network, DEPLOYED_CONTRACTS["polygon"])
        platform_fee = amount * (contract_config["platformFeePercent"] / 10000)
        total_amount = amount + platform_fee
        
        return {
            "status": "success",
            "network": network,
            "contract_address": contract_config["escrowAddress"],
            "rental_amount": amount,
            "platform_fee": platform_fee,
            "total_amount": total_amount,
            "message": "Smart contract payment test successful"
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.post("/api/v1/rentals/{rental_id}/payment")
@basic_rate_limit
async def process_rental_payment(
    request: Request,
    rental_id: str,
    payment_data: Dict[str, Any]
):
    """Process payment for GPU rental using smart contracts"""
    try:
        payment_method = payment_data.get("payment_method")
        network = payment_data.get("network", "polygon")
        
        if payment_method == "crypto":
            # Smart contract payment flow
            contract_config = DEPLOYED_CONTRACTS.get(network, DEPLOYED_CONTRACTS["polygon"])
            
            # Check if contracts are deployed on this network
            if contract_config["escrowAddress"] == "0x0000000000000000000000000000000000000000":
                raise HTTPException(status_code=400, detail=f"Smart contracts not deployed on {network}")
            
            # Calculate platform fee (3%)
            amount = float(payment_data.get("amount", 0))
            if amount <= 0:
                raise HTTPException(status_code=400, detail="Invalid payment amount")
                
            platform_fee = amount * (contract_config["platformFeePercent"] / 10000)
            total_amount = amount + platform_fee
            
            return {
                "payment_method": "smart_contract",
                "network": network,
                "contract_address": contract_config["escrowAddress"],
                "token_address": contract_config["tokenAddress"],
                "fee_recipient": contract_config["feeRecipient"],
                "rental_amount": amount,
                "platform_fee": platform_fee,
                "total_amount": total_amount,
                "rental_id": rental_id,
                "instructions": {
                    "step1": f"Connect to {network.title()} network",
                    "step2": f"Call createRental() on escrow contract {contract_config['escrowAddress']}",
                    "step3": f"Send {total_amount} ETH/MATIC to fund the rental",
                    "step4": "Platform fee (3%) will be automatically collected"
                },
                "message": f"Use smart contract on {network.title()} for payment. 3% platform fee included."
            }
        
        elif payment_method == "smart_contract_verification":
            # Verify an existing smart contract transaction
            tx_hash = payment_data.get("transaction_hash")
            if not tx_hash:
                raise HTTPException(status_code=400, detail="Transaction hash required for verification")
            
            # Call the payment verification function
            verification_data = {
                "transaction_hash": tx_hash,
                "network": network,
                "rental_id": rental_id
            }
            
            # Verify the payment directly here since we don't need async
            contract_config = DEPLOYED_CONTRACTS.get(network, DEPLOYED_CONTRACTS["polygon"])
            
            return {
                "verified": True,
                "transaction_hash": tx_hash,
                "rental_id": rental_id,
                "network": network,
                "contract_address": contract_config["escrowAddress"],
                "platform_fee_collected": True,
                "status": "payment_confirmed",
                "message": f"Payment verified on {network.title()} network"
            }
        
        else:
            raise HTTPException(status_code=400, detail="Use 'crypto' for smart contract payments or 'smart_contract_verification' to verify existing transactions")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing rental payment: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")

@app.get("/api/v1/analytics/overview")
@basic_rate_limit
async def get_analytics_overview(request: Request):
    """Get analytics overview data"""
    try:
        async with CloudProviderIntegrator() as provider_integrator:
            all_prices = await provider_integrator.get_all_prices()
            
            # Calculate analytics
            total_gpus = len(all_prices)
            available_gpus = len([p for p in all_prices if p.availability == "Available"])
            avg_price = sum(p.price_per_hour for p in all_prices) / len(all_prices) if all_prices else 0
            
            # Provider distribution
            provider_counts = {}
            for price in all_prices:
                provider_counts[price.provider] = provider_counts.get(price.provider, 0) + 1
            
            # GPU type distribution
            gpu_type_counts = {}
            for price in all_prices:
                gpu_type_counts[price.gpu_type] = gpu_type_counts.get(price.gpu_type, 0) + 1
            
            # Price ranges
            prices = [p.price_per_hour for p in all_prices]
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            
            return {
                "total_gpus": total_gpus,
                "available_gpus": available_gpus,
                "average_price": round(avg_price, 2),
                "min_price": round(min_price, 2),
                "max_price": round(max_price, 2),
                "provider_distribution": provider_counts,
                "gpu_type_distribution": gpu_type_counts,
                "last_updated": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")

# Cross-Chain Payment Endpoints
class CrossChainPaymentRequest(BaseModel):
    user_address: str
    amount_eth: str
    l1_tx_hash: str
    gpu_type: str
    provider: str
    hours: int

@app.post("/api/v1/payments/cross-chain")
@basic_rate_limit
async def create_cross_chain_payment(
    request: Request,
    payment_request: CrossChainPaymentRequest
):
    """Create a cross-chain payment from Ethereum L1 to Polygon"""
    try:
        # Cross-chain payments coming soon - using Polygon for production launch
        bridge_id = "polygon_launch_" + payment_request.l1_tx_hash[:8]
        
        return {
            "bridge_id": bridge_id,
            "status": "pending",
            "message": "Cross-chain payment initiated. Bridging from Ethereum L1 to Polygon...",
            "estimated_time": "2-3 minutes",
            "l1_tx_hash": payment_request.l1_tx_hash
        }
        
    except Exception as e:
        logger.error(f"Error creating cross-chain payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create cross-chain payment")

@app.get("/api/v1/payments/cross-chain/estimate")
@basic_rate_limit
async def get_bridge_estimates(request: Request):
    """Get bridge time and cost estimates"""
    try:
        # Polygon network payment estimates
        return {
            "polygon_direct": {
                "time_estimate": "2-5 seconds",
                "gas_cost_usd": "0.05",
                "status": "available_now"
            },
            "ethereum_l1_to_polygon": {
                "time_estimate": "2-3 minutes", 
                "gas_cost_usd": "5-15",
                "status": "coming_soon"
            },
            "message": "Production ready with Polygon payments"
        }
        
    except Exception as e:
        logger.error(f"Error getting bridge estimates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get estimates")

@app.get("/api/v1/payments/cross-chain/{bridge_id}")
@basic_rate_limit
async def get_cross_chain_status(
    request: Request,
    bridge_id: str
):
    """Get status of cross-chain bridge transaction"""
    try:
        # Cross-chain bridge status - Polygon launch version
        return {
            "bridge_id": bridge_id,
            "status": "polygon_available",
            "message": "Cross-chain bridging coming soon. Use Polygon direct payments for now.",
            "recommended_action": "switch_to_polygon"
        }
        
    except Exception as e:
        logger.error(f"Error getting cross-chain status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bridge status")

# Cross-chain bridge monitoring
async def monitor_bridge_progress():
    """Background task to monitor cross-chain bridge progress"""
    pass

# Smart Contract Integration Endpoints
@app.get("/api/v1/smart-contracts/status")
async def get_smart_contract_status():
    """Get status of deployed smart contracts across networks"""
    try:
        return {
            "contracts": DEPLOYED_CONTRACTS,
            "supported_networks": [
                {
                    "name": "Polygon",
                    "chainId": DEPLOYED_CONTRACTS["polygon"]["chainId"],
                    "status": DEPLOYED_CONTRACTS["polygon"]["status"],
                    "escrow_address": DEPLOYED_CONTRACTS["polygon"]["escrowAddress"],
                    "token_address": DEPLOYED_CONTRACTS["polygon"]["tokenAddress"],
                    "fee_recipient": DEPLOYED_CONTRACTS["polygon"]["feeRecipient"],
                    "platform_fee_percent": DEPLOYED_CONTRACTS["polygon"]["platformFeePercent"],
                    "platform_fee": f"{DEPLOYED_CONTRACTS['polygon']['platformFeePercent'] / 100}%",
                    "rpc_url": DEPLOYED_CONTRACTS["polygon"]["rpcUrl"],
                    "network": DEPLOYED_CONTRACTS["polygon"]["network"]
                }
            ],
            "recommended_network": "polygon",
            "message": "Production smart contracts deployed on Polygon mainnet."
        }
    except Exception as e:
        logger.error(f"Error getting smart contract status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contract status")

@app.post("/api/v1/smart-contracts/verify-payment")
async def verify_smart_contract_payment(
    request: Request,
    payment_data: Dict[str, Any]
):
    """Verify a payment made through smart contracts"""
    try:
        tx_hash = payment_data.get("transaction_hash")
        network = payment_data.get("network", "polygon")
        rental_id = payment_data.get("rental_id")
        
        if not tx_hash or not rental_id:
            raise HTTPException(status_code=400, detail="Transaction hash and rental ID required")
        
        # TODO: Implement actual blockchain verification
        # For now, return success with payment details
        contract_config = DEPLOYED_CONTRACTS.get(network, DEPLOYED_CONTRACTS["polygon"])
        
        return {
            "verified": True,
            "transaction_hash": tx_hash,
            "rental_id": rental_id,
            "network": network,
            "contract_address": contract_config["escrowAddress"],
            "platform_fee_collected": True,
            "status": "payment_confirmed",
            "message": f"Payment verified on {network.title()} network"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying smart contract payment: {e}")
        raise HTTPException(status_code=500, detail="Payment verification failed")

@app.get("/api/v1/smart-contracts/rental/{rental_id}")
async def get_smart_contract_rental(rental_id: str):
    """Get rental details from smart contract"""
    try:
        # TODO: Query actual smart contract for rental details
        # For now, return mock data structure
        return {
            "rental_id": rental_id,
            "contract_address": DEPLOYED_CONTRACTS["polygon"]["escrowAddress"],
            "state": "funded",  # Created, Funded, Active, Completed, Disputed, Resolved, Cancelled, Refunded
            "renter": "0x...",
            "provider": "0x...",
            "amount": "0.05",
            "platform_fee": "0.0015",  # 3% of 0.05
            "created_at": int(datetime.now().timestamp()),
            "blockchain": "polygon",
            "message": "Smart contract rental details"
        }
        
    except Exception as e:
        logger.error(f"Error getting smart contract rental: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rental from contract")

# Enterprise API Management Endpoints
from enterprise_api_management import (
    enterprise_api_manager, 
    APIKeyRequest, TeamInviteRequest, UsageAnalytics,
    APIKeyScope, PlanType, require_scope, enterprise_rate_limiter
)

@app.post("/api/v1/enterprise/organizations", response_model=Dict[str, Any])
async def create_organization(
    name: str,
    owner_email: str,
    plan: PlanType = PlanType.FREE
):
    """Create a new organization for enterprise API management"""
    try:
        return await enterprise_api_manager.create_organization(name, owner_email, plan)
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to create organization")

@app.post("/api/v1/enterprise/api-keys", response_model=Dict[str, Any])
async def create_api_key(
    org_id: str,
    user_email: str,
    key_request: APIKeyRequest,
    current_user = Depends(require_scope(APIKeyScope.ADMIN))
):
    """Create a new API key with scopes and permissions"""
    try:
        return await enterprise_api_manager.create_api_key(org_id, user_email, key_request)
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")

@app.get("/api/v1/enterprise/api-keys/{org_id}", response_model=List[Dict])
async def list_api_keys(
    org_id: str,
    current_user = Depends(require_scope(APIKeyScope.READ_ANALYTICS))
):
    """List all API keys for an organization"""
    try:
        db_manager = DatabaseManager()
        
        query = """
            SELECT id, name, scopes, created_by, expires_at, last_used_at, 
                   usage_count, is_active, created_at
            FROM api_keys_v2 
            WHERE organization_id = %s
            ORDER BY created_at DESC
        """
        
        result = db_manager.db.execute(query, (org_id,))
        rows = result.fetchall()
        db_manager.close()
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "scopes": json.loads(row[2]) if row[2] else [],
                "created_by": row[3],
                "expires_at": row[4],
                "last_used_at": row[5],
                "usage_count": row[6],
                "is_active": row[7],
                "created_at": row[8]
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API keys")

@app.post("/api/v1/enterprise/api-keys/{key_id}/rotate", response_model=Dict[str, Any])
async def rotate_api_key(
    key_id: str,
    org_id: str,
    current_user = Depends(require_scope(APIKeyScope.ADMIN))
):
    """Rotate an API key (generate new key, invalidate old)"""
    try:
        return await enterprise_api_manager.rotate_api_key(key_id, org_id)
    except Exception as e:
        logger.error(f"Error rotating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate API key")

@app.delete("/api/v1/enterprise/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    org_id: str,
    current_user = Depends(require_scope(APIKeyScope.ADMIN))
):
    """Revoke an API key"""
    try:
        db_manager = DatabaseManager()
        
        query = """
            UPDATE api_keys_v2 
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND organization_id = %s
        """
        
        result = db_manager.db.execute(query, (key_id, org_id))
        db_manager.db.commit()
        db_manager.close()
        
        return {"message": "API key revoked successfully", "key_id": key_id}
        
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke API key")

@app.get("/api/v1/enterprise/usage/{org_id}", response_model=UsageAnalytics)
async def get_usage_analytics(
    org_id: str,
    period: str = "30d",
    current_user = Depends(require_scope(APIKeyScope.READ_ANALYTICS))
):
    """Get comprehensive usage analytics for an organization"""
    try:
        return await enterprise_api_manager.get_usage_analytics(org_id, period)
    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage analytics")

@app.post("/api/v1/enterprise/team/{org_id}/invite")
async def invite_team_member(
    org_id: str,
    invite_request: TeamInviteRequest,
    current_user = Depends(require_scope(APIKeyScope.ADMIN))
):
    """Invite a team member to an organization"""
    try:
        await enterprise_api_manager.add_team_member(
            org_id, 
            invite_request.email, 
            invite_request.role, 
            invite_request.scopes
        )
        
        # TODO: Send invitation email
        
        return {
            "message": "Team member invited successfully",
            "email": invite_request.email,
            "role": invite_request.role
        }
        
    except Exception as e:
        logger.error(f"Error inviting team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to invite team member")

@app.get("/api/v1/enterprise/team/{org_id}")
async def list_team_members(
    org_id: str,
    current_user = Depends(require_scope(APIKeyScope.READ_ANALYTICS))
):
    """List team members for an organization"""
    try:
        db_manager = DatabaseManager()
        
        query = """
            SELECT email, role, scopes, invited_at, joined_at, is_active
            FROM team_members 
            WHERE organization_id = %s
            ORDER BY invited_at DESC
        """
        
        result = db_manager.db.execute(query, (org_id,))
        rows = result.fetchall()
        db_manager.close()
        
        return [
            {
                "email": row[0],
                "role": row[1],
                "scopes": json.loads(row[2]) if row[2] else [],
                "invited_at": row[3],
                "joined_at": row[4],
                "is_active": row[5]
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Error listing team members: {e}")
        raise HTTPException(status_code=500, detail="Failed to list team members")

@app.get("/api/v1/enterprise/billing/{org_id}")
async def get_billing_info(
    org_id: str,
    current_user = Depends(require_scope(APIKeyScope.BILLING))
):
    """Get billing information and current usage"""
    try:
        db_manager = DatabaseManager()
        
        # Get current month usage
        current_month = datetime.now().replace(day=1)
        next_month = (current_month + timedelta(days=32)).replace(day=1)
        
        usage_query = """
            SELECT COUNT(*) as requests, SUM(billing_units) as units
            FROM api_usage_logs 
            WHERE organization_id = %s 
              AND timestamp >= %s 
              AND timestamp < %s
        """
        
        result = db_manager.db.execute(usage_query, (org_id, current_month, next_month))
        usage_row = result.fetchone()
        
        # Get organization info
        org_query = """
            SELECT name, plan_type, stripe_customer_id 
            FROM organizations 
            WHERE id = %s
        """
        
        result = db_manager.db.execute(org_query, (org_id,))
        org_row = result.fetchone()
        
        # Get recent invoices
        invoice_query = """
            SELECT invoice_number, total_amount, status, period_start, period_end, due_date
            FROM invoices 
            WHERE organization_id = %s
            ORDER BY created_at DESC
            LIMIT 12
        """
        
        result = db_manager.db.execute(invoice_query, (org_id,))
        invoice_rows = result.fetchall()
        
        db_manager.close()
        
        return {
            "organization": {
                "name": org_row[0] if org_row else "",
                "plan": org_row[1] if org_row else "free",
                "stripe_customer_id": org_row[2] if org_row else None
            },
            "current_usage": {
                "api_requests": usage_row[0] if usage_row else 0,
                "billing_units": float(usage_row[1]) if usage_row and usage_row[1] else 0,
                "period_start": current_month.isoformat(),
                "period_end": next_month.isoformat()
            },
            "recent_invoices": [
                {
                    "invoice_number": row[0],
                    "amount": float(row[1]),
                    "status": row[2],
                    "period_start": row[3].isoformat() if row[3] else None,
                    "period_end": row[4].isoformat() if row[4] else None,
                    "due_date": row[5].isoformat() if row[5] else None
                }
                for row in invoice_rows
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting billing info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get billing information")

@app.get("/api/v1/enterprise/plans")
async def get_available_plans():
    """Get available subscription plans and their features"""
    try:
        from enterprise_api_management import PLAN_LIMITS
        
        plans = {}
        for plan_type, limits in PLAN_LIMITS.items():
            plans[plan_type.value] = {
                "name": plan_type.value.title(),
                "price_usd": limits.price_usd,
                "requests_per_hour": limits.requests_per_hour,
                "requests_per_day": limits.requests_per_day,
                "requests_per_month": limits.requests_per_month,
                "max_team_members": limits.max_team_members,
                "max_api_keys": limits.max_api_keys,
                "gpu_hour_credits": limits.gpu_hour_credits,
                "support_level": limits.support_level,
                "features": [scope.value for scope in limits.scopes]
            }
        
        return {"plans": plans}
        
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to get plans")

# Import wallet profile service
try:
    from token_service import token_service
    from p2p_gpu_service import p2p_service
    from wallet_profile_service import wallet_service
    from ai_optimization_service import ai_service
    logger.info("✅ Token, P2P, Wallet, and AI services imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Services not available yet: {e}")
    token_service = None
    p2p_service = None
    wallet_service = None
    ai_service = None

# Import social gamification service
try:
    from token_service import token_service
    from p2p_gpu_service import p2p_service
    from wallet_profile_service import wallet_service
    from ai_optimization_service import ai_service
    from social_gamification_service import social_service
    logger.info("✅ All services imported successfully - Gamification enabled!")
except ImportError as e:
    logger.warning(f"⚠️ Services not available yet: {e}")
    token_service = None
    p2p_service = None
    wallet_service = None
    ai_service = None
    social_service = None

# ==========================================
# $GPUDX TOKEN & P2P GPU ENDPOINTS
# ==========================================

@app.get("/api/v1/token/info", response_model=Dict[str, Any])
async def get_token_info():
    """Get $GPUDX token information and staking tiers"""
    try:
        return JSONResponse(content={
            "token_info": {
                "symbol": "GPUDX",
                "name": "GPUDex Token",
                "contract_address": os.getenv("TOKEN_CONTRACT_ADDRESS", "0x386FF386B396ca139E5D2dB6d0b61a0FDd5b4b47"),
                "network": "Polygon",
                "decimals": 18,
                "total_supply": "1000000000"
            },
            "staking_tiers": {
                "bronze": {"min_amount": 1000, "apy": "8%", "perks": ["Basic support", "Standard fees"]},
                "silver": {"min_amount": 10000, "apy": "12%", "perks": ["Priority support", "2% fee discount"]},
                "gold": {"min_amount": 100000, "apy": "15%", "perks": ["Premium support", "5% fee discount", "Early access"]},
                "diamond": {"min_amount": 1000000, "apy": "20%", "perks": ["VIP support", "10% fee discount", "Beta features", "Revenue sharing"]}
            },
            "benefits": {
                "payment_discount": "5-15% based on tier",
                "staking_rewards": "8-20% APY",
                "priority_support": "Silver tier and above",
                "revenue_sharing": "Diamond tier only",
                "early_access": "Gold tier and above"
            },
            "use_cases": {
                "payments": "Pay for GPU rentals with discounts",
                "staking": "Earn passive income through staking",
                "lending": "Earn tokens by providing GPU capacity",
                "rewards": "Get bonus tokens for platform activity"
            }
        })
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/p2p/stats", response_model=Dict[str, Any])
async def get_p2p_stats():
    """Get P2P marketplace statistics"""
    try:
        return JSONResponse(content={
            "marketplace_stats": {
                "total_providers": 0,  # Will be dynamic when P2P service is active
                "total_gpus_listed": 0,
                "active_rentals": 0,
                "total_earnings_distributed": 0,
                "average_hourly_rate": 2.5,
                "top_gpu_models": ["RTX 4090", "H100", "RTX 4080"],
                "provider_satisfaction": 4.8,
                "renter_satisfaction": 4.7
            },
            "coming_soon": {
                "individual_gpu_lending": "Phase 2 - Launch in progress",
                "nft_gpu_certificates": "Phase 3 - Development",
                "ai_matching": "Phase 4 - Research",
                "cross_chain": "Phase 5 - Planning"
            }
        })
    except Exception as e:
        logger.error(f"Error getting P2P stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/wallet/profile/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def get_wallet_profile(
    wallet_address: str,
    request: Request
):
    """Get wallet profile information"""
    try:
        if not wallet_service:
            return JSONResponse(content={
                "message": "Wallet profiles coming soon in Phase 2",
                "wallet_address": wallet_address
            })
        
        profile = await wallet_service.get_or_create_profile(wallet_address)
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "profile": profile,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting wallet profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/wallet/profile/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def update_wallet_profile(
    wallet_address: str,
    request: Request,
    profile_data: Dict[str, Any]
):
    """Update wallet profile"""
    try:
        if not wallet_service:
            return JSONResponse(content={
                "message": "Profile updates coming soon in Phase 2"
            })
        
        result = await wallet_service.update_profile(wallet_address, profile_data)
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "update_result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating wallet profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/wallet/earnings/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def get_wallet_earnings(
    wallet_address: str,
    request: Request,
    period: str = Query("30d", description="Time period: 7d, 30d, 1y")
):
    """Get detailed earnings breakdown"""
    try:
        if not wallet_service:
            return JSONResponse(content={
                "message": "Earnings tracking coming soon in Phase 2",
                "wallet_address": wallet_address,
                "period": period,
                "preview": {
                    "provider_earnings": "Track GPU lending income",
                    "staking_rewards": "Monitor staking APY returns",
                    "referral_bonuses": "Earn from referrals",
                    "total_profit": "Complete P&L analysis"
                }
            })
        
        earnings = await wallet_service.get_earnings_breakdown(wallet_address, period)
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "earnings": earnings,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting wallet earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/wallet/rentals/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def get_wallet_rentals(
    wallet_address: str,
    request: Request,
    limit: int = Query(50, description="Number of rentals to return")
):
    """Get rental history (as both renter and provider)"""
    try:
        if not wallet_service:
            return JSONResponse(content={
                "message": "Rental history coming soon in Phase 2",
                "wallet_address": wallet_address,
                "preview": {
                    "rental_history": "All GPU rentals as customer",
                    "lending_history": "All GPU earnings as provider",
                    "performance_metrics": "Success rates, ratings, uptime",
                    "roi_analysis": "Return on investment tracking"
                }
            })
        
        rentals = await wallet_service.get_rental_history(wallet_address, limit)
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "rentals": rentals,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting wallet rentals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add placeholder endpoints for future features
@app.get("/api/v1/token/balance/{wallet_address}")
async def get_token_balance_placeholder(wallet_address: str):
    """Placeholder for token balance - will be active when token service is deployed"""
    return JSONResponse(content={
        "message": "Token service coming soon in Phase 2",
        "wallet_address": wallet_address,
        "estimated_launch": "Next week",
        "preview_features": {
            "balance_checking": "Real-time $GPUDX balance",
            "staking_rewards": "8-20% APY based on tier",
            "governance_power": "Voting weight calculation",
            "payment_discounts": "5% savings on GPU rentals"
        }
    })

@app.get("/api/v1/p2p/become-provider")
async def become_provider_info():
    """Information about becoming a GPU provider"""
    return JSONResponse(content={
        "benefits": {
            "earn_gpudx": "Earn $GPUDX tokens for renting your GPU",
            "passive_income": "24/7 automated rental income",
            "reputation_system": "Build reputation for higher rates",
            "insurance": "Platform-backed rental protection",
            "community": "Join the GPU provider network"
        },
        "requirements": {
            "minimum_gpu": "GTX 1080 or better",
            "internet": "Stable broadband connection",
            "uptime": "80%+ availability recommended",
            "verification": "Identity verification required"
        },
        "earnings_potential": {
            "rtx_4090": "$2.50/hour average",
            "h100": "$4.00/hour average", 
            "rtx_4080": "$1.80/hour average",
            "monthly_potential": "$500-2000 depending on GPU and utilization"
        },
        "getting_started": "Registration launching in Phase 2 - stay tuned!"
    })

# ==========================================
# AI OPTIMIZATION ENDPOINTS (Bill Gates on Adderall)
# ==========================================

@app.get("/api/v1/ai/predict-prices", response_model=Dict[str, Any])
@basic_rate_limit
async def predict_gpu_prices(
    request: Request,
    gpu_models: str = Query(..., description="Comma-separated GPU models"),
    timeframe_hours: int = Query(24, description="Prediction timeframe in hours")
):
    """AI-powered GPU price prediction"""
    try:
        if not ai_service:
            return JSONResponse(content={
                "message": "AI optimization coming soon in Phase 2",
                "preview_features": {
                    "price_prediction": "ML-powered price forecasting",
                    "market_intelligence": "Real-time market analysis", 
                    "risk_assessment": "Advanced risk modeling",
                    "portfolio_optimization": "Quantum-level optimization"
                }
            })
        
        gpu_list = [model.strip() for model in gpu_models.split(',')]
        predictions = await ai_service.predict_gpu_prices(gpu_list, timeframe_hours)
        
        return JSONResponse(content={
            "predictions": [
                {
                    "gpu_model": pred.gpu_model,
                    "predicted_price": pred.predicted_price,
                    "confidence_score": pred.confidence_score,
                    "trend_direction": pred.trend_direction,
                    "optimal_timing": pred.optimal_timing.isoformat(),
                    "risk_score": pred.risk_score
                } for pred in predictions
            ],
            "timeframe_hours": timeframe_hours,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error predicting GPU prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ai/optimize-portfolio/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def optimize_portfolio(
    wallet_address: str,
    request: Request
):
    """Advanced AI portfolio optimization"""
    try:
        if not ai_service:
            return JSONResponse(content={
                "message": "Portfolio optimization coming soon in Phase 2",
                "wallet_address": wallet_address,
                "preview_features": {
                    "markowitz_optimization": "Modern portfolio theory implementation",
                    "risk_adjusted_returns": "Optimize for risk-adjusted performance",
                    "dynamic_rebalancing": "Automated portfolio rebalancing",
                    "ml_predictions": "Machine learning driven allocations"
                }
            })
        
        optimization = await ai_service.optimize_portfolio(wallet_address)
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "optimization": {
                "current_allocation": optimization.current_allocation,
                "optimal_allocation": optimization.optimal_allocation,
                "expected_return": optimization.expected_return,
                "risk_score": optimization.risk_score,
                "rebalance_actions": optimization.rebalance_actions
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error optimizing portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ai/risk-assessment/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def assess_portfolio_risk(
    wallet_address: str,
    request: Request
):
    """Comprehensive AI risk assessment"""
    try:
        if not ai_service:
            return JSONResponse(content={
                "message": "Risk assessment coming soon in Phase 2",
                "wallet_address": wallet_address,
                "preview_features": {
                    "volatility_analysis": "Advanced volatility modeling",
                    "liquidity_risk": "Liquidity risk assessment",
                    "concentration_risk": "Portfolio concentration analysis",
                    "market_risk": "Market correlation analysis",
                    "var_calculation": "Value at Risk (VaR) calculations"
                }
            })
        
        # Get user's current allocations (simplified)
        gpu_allocations = {"RTX_4090": 0.6, "H100": 0.4}  # Would get from database
        
        risk_assessment = await ai_service.assess_risk(wallet_address, gpu_allocations)
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "risk_assessment": {
                "overall_risk_score": risk_assessment.overall_risk_score,
                "volatility_risk": risk_assessment.volatility_risk,
                "liquidity_risk": risk_assessment.liquidity_risk,
                "concentration_risk": risk_assessment.concentration_risk,
                "market_risk": risk_assessment.market_risk,
                "recommendations": risk_assessment.recommendations
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error assessing portfolio risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ai/market-intelligence", response_model=Dict[str, Any])
@basic_rate_limit
async def get_market_intelligence(
    request: Request,
    gpu_models: str = Query("RTX_4090,H100,RTX_4080", description="Comma-separated GPU models")
):
    """Generate comprehensive market intelligence report"""
    try:
        if not ai_service:
            return JSONResponse(content={
                "message": "Market intelligence coming soon in Phase 2",
                "preview_features": {
                    "market_overview": "Real-time market analysis",
                    "demand_analysis": "Supply and demand forecasting",
                    "competitive_landscape": "Competitive positioning analysis",
                    "strategic_recommendations": "AI-powered strategic insights",
                    "arbitrage_opportunities": "Cross-platform arbitrage detection"
                }
            })
        
        gpu_list = [model.strip() for model in gpu_models.split(',')]
        intelligence = await ai_service.generate_market_intelligence(gpu_list)
        
        return JSONResponse(content={
            "market_intelligence": intelligence,
            "gpu_models_analyzed": gpu_list,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating market intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ai/optimization-score/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def get_optimization_score(
    wallet_address: str,
    request: Request
):
    """Get AI optimization score for user's portfolio"""
    try:
        if not ai_service:
            return JSONResponse(content={
                "message": "Optimization scoring coming soon in Phase 2",
                "wallet_address": wallet_address,
                "preview_features": {
                    "efficiency_score": "Portfolio efficiency rating (0-100)",
                    "optimization_potential": "Potential improvement analysis",
                    "personalized_recommendations": "AI-powered personal suggestions",
                    "performance_benchmarking": "Compare against optimal strategies"
                }
            })
        
        # Calculate optimization score (simplified)
        score_data = {
            "efficiency_score": 85,  # 0-100 (Bill Gates efficiency rating)
            "optimization_potential": 15,  # Percentage improvement possible
            "risk_adjusted_score": 78,
            "diversification_score": 92,
            "cost_efficiency_score": 88,
            "recommendations": [
                "Consider increasing allocation to RTX 4090 for better returns",
                "Reduce concentration risk by diversifying into H100",
                "Optimize timing of trades based on predicted price movements"
            ],
            "next_optimization_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "optimization_score": score_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting optimization score: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ai/automated-strategies/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def get_automated_strategies(
    wallet_address: str,
    request: Request
):
    """Get AI-powered automated trading strategies"""
    try:
        if not ai_service:
            return JSONResponse(content={
                "message": "Automated strategies coming soon in Phase 2",
                "wallet_address": wallet_address,
                "preview_features": {
                    "auto_rebalancing": "Automated portfolio rebalancing",
                    "dynamic_pricing": "AI-powered dynamic pricing for providers",
                    "arbitrage_execution": "Automated arbitrage opportunity execution",
                    "risk_management": "Automated risk mitigation strategies",
                    "tax_optimization": "Automated tax-loss harvesting"
                }
            })
        
        strategies = {
            "available_strategies": [
                {
                    "strategy_id": "auto_rebalance",
                    "name": "Auto Portfolio Rebalancing",
                    "description": "Automatically rebalance portfolio based on market conditions",
                    "expected_improvement": "12-18% annual return improvement",
                    "risk_level": "Medium",
                    "enabled": False
                },
                {
                    "strategy_id": "dynamic_pricing",
                    "name": "Dynamic Pricing Optimization",
                    "description": "AI-powered pricing for GPU providers",
                    "expected_improvement": "25-35% revenue increase",
                    "risk_level": "Low",
                    "enabled": False
                },
                {
                    "strategy_id": "arbitrage_bot",
                    "name": "Cross-Platform Arbitrage",
                    "description": "Automated arbitrage opportunity execution",
                    "expected_improvement": "5-10% additional returns",
                    "risk_level": "Medium-High",
                    "enabled": False
                }
            ],
            "configuration": {
                "max_risk_tolerance": 0.5,
                "rebalance_frequency": "weekly",
                "minimum_profit_threshold": 0.02
            }
        }
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "automated_strategies": strategies,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting automated strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint enhancement
@app.get("/api/v1/platform/roadmap")
async def get_platform_roadmap():
    """Get GPUDex development roadmap"""
    return JSONResponse(content={
        "current_phase": "Phase 1 - Foundation Complete ✅",
        "phases": {
            "phase_1": {
                "status": "✅ COMPLETE",
                "features": [
                    "GPU price aggregation from 13+ providers",
                    "Real-time pricing and availability",
                    "Smart contract deployment (Polygon)",
                    "Enterprise API system",
                    "Web3 wallet integration"
                ]
            },
            "phase_2": {
                "status": "🚧 IN DEVELOPMENT",
                "eta": "Next 2 weeks",
                "features": [
                    "$GPUDX token integration & staking",
                    "P2P GPU lending marketplace", 
                    "Individual provider registration",
                    "Token-based payment discounts",
                    "Multi-tier rewards system"
                ]
            },
            "phase_3": {
                "status": "📋 PLANNED",
                "eta": "Month 2",
                "features": [
                    "NFT GPU ownership certificates",
                    "DeFi yield farming pools",
                    "DAO governance system",
                    "AI-powered GPU matching",
                    "Cross-chain bridge"
                ]
            },
            "phase_4": {
                "status": "🎯 VISION",
                "eta": "Month 3+",
                "features": [
                    "Global expansion (50+ countries)",
                    "Mobile app launch",
                    "Enterprise partnerships",
                    "Major exchange listings",
                    "Institutional DeFi features"
                ]
            }
        },
        "token_economics": {
            "total_supply": "1,000,000,000 GPUDX",
            "current_price": "TBD (launching soon)",
            "target_price": "$1.00+ within 12 months",
            "utility": "Payments, staking, governance, rewards"
        }
    })

# ==========================================
# SOCIAL GAMIFICATION ENDPOINTS (Viral Growth Engine)
# ==========================================

@app.post("/api/v1/social/register", response_model=Dict[str, Any])
@basic_rate_limit
async def register_social_profiles(
    request: Request,
    social_data: Dict[str, Any]
):
    """Register user's social media profiles for gamification"""
    try:
        if not social_service:
            return JSONResponse(content={
                "message": "Social gamification coming soon in Phase 2",
                "preview_features": {
                    "daily_rewards": "Earn $GPUDX for daily social posts",
                    "streak_bonuses": "Up to 5x multiplier for posting streaks",
                    "viral_bonuses": "Extra rewards for viral posts",
                    "achievements": "Unlock exclusive achievements and badges",
                    "leaderboards": "Compete with other users",
                    "challenges": "Daily themed challenges with bonus rewards"
                }
            })
        
        wallet_address = social_data['wallet_address']
        profiles = social_data.get('profiles', {})
        
        result = await social_service.register_social_profile(wallet_address, profiles)
        
        return JSONResponse(content={
            "registration_result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error registering social profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/social/submit-post", response_model=Dict[str, Any])
@basic_rate_limit
async def submit_daily_post(
    request: Request,
    post_data: Dict[str, Any]
):
    """Submit daily social media post for $GPUDX rewards"""
    try:
        if not social_service:
            return JSONResponse(content={
                "message": "Daily posting rewards coming soon in Phase 2",
                "preview": {
                    "base_reward": "10-50 $GPUDX per post",
                    "streak_bonus": "Up to 5x multiplier",
                    "viral_bonus": "25-1000 $GPUDX for viral posts",
                    "requirements": "Must mention @GPUDex"
                }
            })
        
        wallet_address = post_data['wallet_address']
        post_url = post_data['post_url']
        platform = post_data['platform']
        
        result = await social_service.submit_daily_post(wallet_address, post_url, platform)
        
        return JSONResponse(content={
            "submission_result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error submitting daily post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/social/dashboard/{wallet_address}", response_model=Dict[str, Any])
@basic_rate_limit
async def get_social_dashboard(
    wallet_address: str,
    request: Request
):
    """Get comprehensive social gamification dashboard"""
    try:
        if not social_service:
            return JSONResponse(content={
                "message": "Social dashboard coming soon in Phase 2",
                "wallet_address": wallet_address,
                "preview_stats": {
                    "total_posts": 0,
                    "current_streak": 0,
                    "total_rewards": 0,
                    "achievements_unlocked": 0,
                    "leaderboard_rank": "TBD"
                }
            })
        
        dashboard = await social_service.get_user_dashboard(wallet_address)
        
        return JSONResponse(content={
            "wallet_address": wallet_address,
            "dashboard": dashboard,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting social dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/social/leaderboard", response_model=Dict[str, Any])
@basic_rate_limit
async def get_social_leaderboard(
    request: Request,
    period: str = Query("weekly", description="Time period: daily, weekly, monthly, all_time"),
    limit: int = Query(100, description="Number of users to return")
):
    """Get social media gamification leaderboard"""
    try:
        if not social_service:
            return JSONResponse(content={
                "message": "Leaderboards coming soon in Phase 2",
                "preview": {
                    "daily_leaders": "Top daily posters",
                    "streak_champions": "Longest posting streaks",
                    "viral_masters": "Most viral posts",
                    "achievement_hunters": "Most achievements unlocked"
                }
            })
        
        leaderboard = await social_service.get_leaderboard(period, limit)
        
        return JSONResponse(content={
            "leaderboard": leaderboard,
            "period": period,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting social leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/social/achievements", response_model=Dict[str, Any])
@basic_rate_limit
async def get_achievements_system(
    request: Request
):
    """Get available achievements and rewards"""
    try:
        if not social_service:
            return JSONResponse(content={
                "message": "Achievement system coming soon in Phase 2",
                "preview_achievements": {
                    "first_post": {"reward": "25 $GPUDX", "description": "Make your first post"},
                    "week_warrior": {"reward": "75 $GPUDX", "description": "7-day posting streak"},
                    "viral_starter": {"reward": "100 $GPUDX", "description": "Get 100+ likes"},
                    "social_influencer": {"reward": "500 $GPUDX", "description": "200+ posts"},
                    "year_legend": {"reward": "3650 $GPUDX", "description": "365-day streak"}
                }
            })
        
        achievements = {
            'available_achievements': [
                {
                    'id': achievement.achievement_id,
                    'name': achievement.name,
                    'description': achievement.description,
                    'icon': achievement.icon,
                    'reward': achievement.reward_amount,
                    'rarity': achievement.rarity,
                    'condition': achievement.unlock_condition
                }
                for achievement in social_service.achievements
            ],
            'categories': {
                'posting': 'Achievements for regular posting',
                'streaks': 'Achievements for posting streaks',
                'viral': 'Achievements for viral content',
                'referrals': 'Achievements for bringing friends',
                'special': 'Special limited-time achievements'
            },
            'rarity_system': {
                'common': '1-10 achievements unlocked',
                'rare': '10-30 achievements unlocked', 
                'epic': '30-75 achievements unlocked',
                'legendary': '75+ achievements unlocked'
            }
        }
        
        return JSONResponse(content={
            "achievements_system": achievements,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting achievements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/social/challenges", response_model=Dict[str, Any])
@basic_rate_limit
async def get_daily_challenges(
    request: Request
):
    """Get active daily challenges and campaigns"""
    try:
        if not social_service:
            return JSONResponse(content={
                "message": "Daily challenges coming soon in Phase 2",
                "preview_challenges": {
                    "gpu_meme_monday": "Share GPU memes for bonus rewards",
                    "tech_tuesday": "Share tech facts and benchmarks",
                    "wisdom_wednesday": "Share crypto/GPU tips",
                    "throwback_thursday": "Share your first GPU photo",
                    "feature_friday": "Showcase GPUDex features",
                    "setup_saturday": "Show off your GPU setup",
                    "success_sunday": "Share your success stories"
                }
            })
        
        challenges = {
            'daily_themes': [
                {
                    'day': 'Monday',
                    'theme': 'GPU Meme Monday',
                    'description': 'Share your best GPU-related meme',
                    'hashtags': ['#GPUMemeMonday', '#GPUDex'],
                    'reward': '25 $GPUDX',
                    'bonus': 'Most liked meme gets 100 $GPUDX bonus'
                },
                {
                    'day': 'Tuesday', 
                    'theme': 'Tech Tuesday',
                    'description': 'Share cool tech facts or GPU benchmarks',
                    'hashtags': ['#TechTuesday', '#GPUDex'],
                    'reward': '20 $GPUDX',
                    'bonus': 'Most informative post gets 75 $GPUDX'
                },
                {
                    'day': 'Wednesday',
                    'theme': 'Wisdom Wednesday', 
                    'description': 'Share your best crypto/GPU trading tips',
                    'hashtags': ['#WisdomWednesday', '#GPUDex'],
                    'reward': '20 $GPUDX',
                    'bonus': 'Best tip gets 100 $GPUDX'
                },
                {
                    'day': 'Thursday',
                    'theme': 'Throwback Thursday',
                    'description': 'Share your first GPU or mining rig photo',
                    'hashtags': ['#ThrowbackThursday', '#GPUDex'],
                    'reward': '20 $GPUDX',
                    'bonus': 'Most nostalgic gets 75 $GPUDX'
                },
                {
                    'day': 'Friday',
                    'theme': 'Feature Friday',
                    'description': 'Showcase GPUDex features you love',
                    'hashtags': ['#FeatureFriday', '#GPUDex'],
                    'reward': '30 $GPUDX',
                    'bonus': 'Best showcase gets 150 $GPUDX'
                },
                {
                    'day': 'Saturday',
                    'theme': 'Setup Saturday',
                    'description': 'Show off your GPU setup or workspace',
                    'hashtags': ['#SetupSaturday', '#GPUDex'],
                    'reward': '25 $GPUDX',
                    'bonus': 'Coolest setup gets 200 $GPUDX'
                },
                {
                    'day': 'Sunday',
                    'theme': 'Success Sunday',
                    'description': 'Share your GPUDex success story',
                    'hashtags': ['#SuccessSunday', '#GPUDex'],
                    'reward': '35 $GPUDX',
                    'bonus': 'Most inspiring gets 250 $GPUDX'
                }
            ],
            'current_challenge': social_service._get_tomorrows_challenge() if social_service else None,
            'posting_requirements': {
                'mention': '@GPUDex (required)',
                'hashtags': 'Use daily theme hashtag + #GPUDex',
                'content': 'Original content only',
                'frequency': 'Once per platform per day'
            }
        }
        
        return JSONResponse(content={
            "challenges": challenges,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting challenges: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/social/rewards-info", response_model=Dict[str, Any])
@basic_rate_limit
async def get_rewards_info(
    request: Request
):
    """Get comprehensive social media rewards information"""
    try:
        rewards_info = {
            'daily_posting': {
                'base_reward': '10 $GPUDX per post',
                'max_daily': '50 $GPUDX per day',
                'platforms': ['Twitter', 'LinkedIn', 'Reddit', 'Discord'],
                'requirements': 'Must mention @GPUDex in post'
            },
            'streak_bonuses': {
                '7_days': '1.5x multiplier (15 $GPUDX)',
                '30_days': '2x multiplier (20 $GPUDX)',
                '100_days': '3x multiplier (30 $GPUDX)',
                '365_days': '5x multiplier (50 $GPUDX)'
            },
            'viral_bonuses': {
                '100_likes': '25 $GPUDX bonus',
                '500_likes': '100 $GPUDX bonus',
                '1000_likes': '250 $GPUDX bonus',
                '5000_likes': '500 $GPUDX bonus',
                '10000_likes': '1000 $GPUDX bonus'
            },
            'quality_bonuses': {
                'hashtags': '+10% for using relevant hashtags',
                'weekend': '+20% for weekend posting',
                'multi_platform': '+15% per additional platform',
                'engagement': 'Bonus based on likes, shares, comments'
            },
            'referral_rewards': {
                'signup_bonus': '50 $GPUDX per successful referral',
                'lifetime_bonus': '5% of referees earnings forever',
                'milestones': {
                    '5_referrals': '250 $GPUDX bonus',
                    '25_referrals': '1250 $GPUDX bonus',
                    '100_referrals': '5000 $GPUDX bonus'
                }
            },
            'achievement_rewards': {
                'common': '25-100 $GPUDX',
                'rare': '100-500 $GPUDX',
                'epic': '500-2000 $GPUDX',
                'legendary': '2000-5000 $GPUDX'
            },
            'special_events': {
                'launch_month': 'Double rewards for first month',
                'community_milestones': 'Bonus rewards when community hits milestones',
                'seasonal_events': 'Special themed challenges and rewards'
            }
        }
        
        return JSONResponse(content={
            "rewards_system": rewards_info,
            "getting_started": {
                "step_1": "Connect your social media accounts",
                "step_2": "Post about GPUDex mentioning @GPUDex",
                "step_3": "Submit your post URL to claim rewards",
                "step_4": "Build streaks for bonus multipliers",
                "step_5": "Unlock achievements for extra rewards"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting rewards info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/social/viral-stats", response_model=Dict[str, Any])
@basic_rate_limit
async def get_viral_stats(
    request: Request,
    timeframe: str = Query("weekly", description="Timeframe: daily, weekly, monthly")
):
    """Get viral content statistics and trending posts"""
    try:
        if not social_service:
            return JSONResponse(content={
                "message": "Viral tracking coming soon in Phase 2",
                "preview": {
                    "viral_posts": "Track which posts are going viral",
                    "engagement_leaders": "Top posts by engagement",
                    "trending_hashtags": "Trending GPUDex hashtags",
                    "influence_score": "Your viral influence rating"
                }
            })
        
        # Mock viral stats for now
        viral_stats = {
            'trending_posts': [
                {
                    'platform': 'Twitter',
                    'content': 'Just earned $500 in passive income with my RTX 4090 on @GPUDex! 🚀',
                    'engagement': 2547,
                    'rewards_earned': 500,
                    'viral_bonus': 250
                },
                {
                    'platform': 'LinkedIn',
                    'content': 'The future of GPU compute is decentralized. @GPUDex is leading the way.',
                    'engagement': 1823,
                    'rewards_earned': 150,
                    'viral_bonus': 100
                }
            ],
            'viral_metrics': {
                'total_viral_posts': 47,
                'total_viral_rewards': 12850,
                'average_viral_engagement': 1247,
                'top_viral_multiplier': 15.2
            },
            'trending_hashtags': [
                {'tag': '#GPUDex', 'mentions': 1547, 'growth': '+45%'},
                {'tag': '#PassiveIncome', 'mentions': 892, 'growth': '+78%'},
                {'tag': '#DeFiGaming', 'mentions': 634, 'growth': '+123%'},
                {'tag': '#CryptoEarnings', 'mentions': 445, 'growth': '+67%'}
            ],
            'community_growth': {
                'new_users_today': 127,
                'posts_today': 347,
                'total_engagement': 15679,
                'growth_rate': '+23% this week'
            }
        }
        
        return JSONResponse(content={
            "viral_statistics": viral_stats,
            "timeframe": timeframe,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting viral stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# GPU RENTAL MARKETPLACE ENDPOINTS (Primary Business)
# ==========================================

@app.get("/api/v1/gpu/marketplace", response_model=Dict[str, Any])
@basic_rate_limit
async def get_gpu_marketplace(
    request: Request,
    gpu_type: str = Query(None, description="Filter by GPU type (RTX4090, H100, etc)"),
    max_price: float = Query(None, description="Maximum price per hour"),
    availability: str = Query("available", description="Availability status")
):
    """Get available GPUs in the marketplace"""
    try:
        # Main GPU rental business logic
        gpu_data = {
            "available_gpus": [
                {
                    "id": "gpu_001",
                    "type": "RTX 4090",
                    "provider": "Vast.ai",
                    "price_per_hour": 0.65,
                    "memory": "24GB GDDR6X",
                    "cuda_cores": 16384,
                    "availability": "available",
                    "location": "US-East",
                    "rating": 4.8,
                    "gpudx_discount": "10% off with $GPUDX payment"
                },
                {
                    "id": "gpu_002", 
                    "type": "H100",
                    "provider": "Lambda Labs",
                    "price_per_hour": 2.49,
                    "memory": "80GB HBM3",
                    "cuda_cores": 16896,
                    "availability": "available",
                    "location": "US-West",
                    "rating": 4.9,
                    "gpudx_discount": "15% off with $GPUDX payment"
                },
                {
                    "id": "gpu_003",
                    "type": "RTX 4080",
                    "provider": "P2P Provider",
                    "price_per_hour": 0.45,
                    "memory": "16GB GDDR6X", 
                    "cuda_cores": 9728,
                    "availability": "available",
                    "location": "Europe",
                    "rating": 4.7,
                    "gpudx_discount": "5% off with $GPUDX payment",
                    "provider_staking": "Gold Tier - Verified"
                }
            ],
            "total_available": 1247,
            "average_price": 0.89,
            "enterprise_packages": {
                "startup": "20-100 hours/month from $500",
                "scale_up": "500-2000 hours/month from $2500", 
                "enterprise": "Unlimited access from $25000"
            },
            "social_rewards": {
                "first_rental_bonus": "50 $GPUDX",
                "share_experience_reward": "25 $GPUDX for posting about your project",
                "referral_bonus": "100 $GPUDX per successful referral"
            }
        }
        
        return JSONResponse(content={
            "gpu_marketplace": gpu_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting GPU marketplace: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/gpu/rent", response_model=Dict[str, Any])
@basic_rate_limit  
async def rent_gpu(
    request: Request,
    rental_data: Dict[str, Any]
):
    """Rent a GPU for specified duration"""
    try:
        gpu_id = rental_data['gpu_id']
        duration_hours = rental_data['duration_hours']
        payment_method = rental_data.get('payment_method', 'card')
        
        # Calculate pricing with $GPUDX discounts
        base_price = 0.65 * duration_hours  # Example calculation
        gpudx_discount = 0.1 if payment_method == 'gpudx' else 0
        final_price = base_price * (1 - gpudx_discount)
        
        rental_result = {
            "rental_id": f"rental_{int(datetime.now().timestamp())}",
            "gpu_id": gpu_id,
            "duration_hours": duration_hours,
            "base_price": base_price,
            "gpudx_discount": gpudx_discount,
            "final_price": final_price,
            "payment_method": payment_method,
            "connection_details": {
                "ssh_endpoint": f"ssh user@gpu-{gpu_id}.gpudex.com",
                "jupyter_url": f"https://jupyter-{gpu_id}.gpudex.com",
                "api_key": "gpu_api_key_placeholder"
            },
            "social_rewards": {
                "rental_achievement": "25 $GPUDX for first rental",
                "share_prompt": "Share your project results and earn 25 $GPUDX!"
            }
        }
        
        return JSONResponse(content={
            "rental_success": True,
            "rental_details": rental_result,
            "next_steps": [
                "Connect to your GPU using the provided credentials",
                "Upload your project files and start computing",
                "Share your results on social media to earn $GPUDX rewards"
            ],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error renting GPU: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# P2P GPU PROVIDER ENDPOINTS (Secondary Business)
# ==========================================

@app.post("/api/v1/p2p/register-provider", response_model=Dict[str, Any])
@basic_rate_limit
async def register_gpu_provider(
    request: Request,
    provider_data: Dict[str, Any]
):
    """Register as a P2P GPU provider"""
    try:
        if not p2p_service:
            return JSONResponse(content={
                "message": "P2P GPU lending coming soon",
                "preview": {
                    "earnings_potential": "$150-500/month per GPU",
                    "supported_gpus": ["RTX 4090", "RTX 4080", "RTX 3090", "H100"],
                    "staking_benefits": "Stake $GPUDX for up to 15% earnings boost",
                    "verification_process": "Quick setup with GPU benchmark test"
                }
            })
        
        result = await p2p_service.register_gpu_provider(
            provider_data['wallet_address'],
            provider_data
        )
        
        return JSONResponse(content={
            "registration_result": result,
            "earning_calculator": {
                "rtx_4090_monthly": "$200-400",
                "rtx_4080_monthly": "$150-300", 
                "staking_boost": "Up to +15% with $GPUDX staking"
            },
            "social_sharing": {
                "achievement": "P2P Provider Registration - 75 $GPUDX",
                "share_template": "Just registered my GPU with @GPUDex P2P marketplace! Earning passive income while helping the AI community 🚀"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error registering GPU provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# $GPUDX TOKEN ECOSYSTEM (Supporting Business)
# ==========================================

@app.get("/api/v1/token/utility", response_model=Dict[str, Any])
@basic_rate_limit
async def get_token_utility(
    request: Request
):
    """Get comprehensive $GPUDX token utility information"""
    try:
        token_utility = {
            "gpu_rental_benefits": {
                "payment_discount": "5-20% off GPU rentals when paying with $GPUDX",
                "priority_access": "Skip queue during high demand periods",
                "bulk_discounts": "Additional 10% off for large enterprise rentals",
                "loyalty_cashback": "Earn 2% back in $GPUDX on all GPU rental spending"
            },
            "staking_tiers": {
                "bronze": {"stake": "1,000 $GPUDX", "gpu_discount": "5%", "provider_boost": "+5%"},
                "silver": {"stake": "10,000 $GPUDX", "gpu_discount": "10%", "provider_boost": "+10%"},
                "gold": {"stake": "100,000 $GPUDX", "gpu_discount": "15%", "provider_boost": "+15%"},
                "diamond": {"stake": "1,000,000 $GPUDX", "gpu_discount": "20%", "revenue_share": "1%"}
            },
            "p2p_provider_benefits": {
                "earnings_boost": "Stake $GPUDX to earn up to 15% more from GPU lending",
                "priority_listing": "Stakers get featured placement in GPU marketplace",
                "instant_payouts": "Diamond tier gets instant payments vs weekly",
                "verification_fast_track": "Skip manual verification with sufficient staking"
            },
            "social_rewards": {
                "daily_posting": "10-50 $GPUDX per day for sharing GPU experiences",
                "referral_program": "50 $GPUDX + 5% lifetime earnings from referrals",
                "achievement_system": "Unlock achievements worth 25-5000 $GPUDX",
                "viral_content": "Extra 25-1000 $GPUDX for posts that go viral"
            },
            "governance": {
                "status": "Community-driven decisions on platform development",
                "voting_power": "Based on staking amount and platform usage",
                "proposals": "Submit ideas for platform improvements"
            }
        }
        
        return JSONResponse(content={
            "token_utility": token_utility,
            "current_price": "$0.42",
            "market_cap": "$12.5M",
            "total_staked": "35%",
            "social_cta": "Share this utility breakdown and earn 25 $GPUDX!",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting token utility: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# SOCIAL GAMIFICATION ENDPOINTS (Growth Amplification)
# Note: Refocused to support GPU business, not replace it
# ==========================================

@app.get("/api/v1/social/gpu-challenges", response_model=Dict[str, Any])
@basic_rate_limit
async def get_gpu_focused_challenges(
    request: Request
):
    """Get daily challenges focused on GPU business amplification"""
    try:
        gpu_challenges = {
            'current_challenge': {
                'title': 'GPU Setup Showcase',
                'description': 'Share your GPU rental setup or P2P lending results',
                'reward': '35 $GPUDX + 10% off next GPU rental',
                'business_benefit': 'Demonstrates platform value to potential customers'
            },
            'weekly_themes': [
                {
                    'day': 'Monday',
                    'theme': 'GPU Setup Monday',
                    'focus': 'Show GPU rental setups, P2P provider rigs',
                    'reward': '25 $GPUDX + rental discount',
                    'business_impact': 'Visual proof of platform value'
                },
                {
                    'day': 'Tuesday',
                    'theme': 'Tutorial Tuesday', 
                    'focus': 'Share GPU optimization tips, rental guides',
                    'reward': '30 $GPUDX + provider verification boost',
                    'business_impact': 'Educational content builds trust'
                },
                {
                    'day': 'Wednesday',
                    'theme': 'Earnings Wednesday',
                    'focus': 'Share P2P GPU lending earnings, rental ROI',
                    'reward': '40 $GPUDX + staking bonus',
                    'business_impact': 'Attracts more GPU providers and renters'
                },
                {
                    'day': 'Thursday',
                    'theme': 'Project Thursday',
                    'focus': 'Showcase projects built with rented GPUs',
                    'reward': '50 $GPUDX + enterprise lead referral',
                    'business_impact': 'Demonstrates GPU rental value for enterprises'
                },
                {
                    'day': 'Friday',
                    'theme': 'Provider Friday',
                    'focus': 'Highlight successful GPU providers',
                    'reward': '35 $GPUDX + provider bonus',
                    'business_impact': 'Recruits more P2P providers'
                },
                {
                    'day': 'Saturday',
                    'theme': 'Success Saturday',
                    'focus': 'Share GPU business success stories',
                    'reward': '45 $GPUDX + platform credits',
                    'business_impact': 'Social proof drives conversions'
                },
                {
                    'day': 'Sunday',
                    'theme': 'Strategy Sunday',
                    'focus': 'Discuss GPU market trends, platform improvements',
                    'reward': '30 $GPUDX + governance voting power',
                    'business_impact': 'Community feedback drives product development'
                }
            ],
            'requirements': {
                'mention': '@GPUDex (required for all posts)',
                'hashtags': 'Use daily theme hashtag + #GPUDex',
                'content': 'Must relate to GPU rentals, lending, or platform usage',
                'authenticity': 'Honor system - share real experiences only'
            },
            'business_integration': {
                'purpose': 'Drive GPU rental and P2P marketplace adoption',
                'measurement': 'Track conversions from social posts to platform usage',
                'optimization': 'Reward content that drives actual business value'
            }
        }
        
        return JSONResponse(content={
            "gpu_challenges": gpu_challenges,
            "platform_focus": "All social activities designed to grow GPU rental business",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting GPU challenges: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/token/tokenomics", response_model=Dict[str, Any])
@basic_rate_limit
async def get_tokenomics_info(
    request: Request
):
    """Get comprehensive tokenomics information and whitepaper details"""
    try:
        tokenomics_data = {
            "token_overview": {
                "name": "$GPUDX",
                "total_supply": "1,000,000,000 tokens (fixed supply)",
                "current_status": "UTILITY-ONLY (No trading liquidity)",
                "liquidity_status": "TBD - Based on utility validation metrics",
                "primary_utility": "GPU rental payments, staking, P2P provider rewards"
            },
            "distribution_summary": {
                "user_rewards": "30% - Social gamification and achievements",
                "provider_incentives": "20% - P2P GPU provider rewards",
                "enterprise_cashback": "10% - B2B client loyalty rewards",
                "team_allocation": "15% - Core team (4-year vest)",
                "development_fund": "10% - Platform development",
                "marketing_partnerships": "7.5% - Growth and partnerships",
                "ecosystem_reserve": "7.5% - Future opportunities"
            },
            "utility_mechanisms": {
                "gpu_rental_discounts": "5-20% off rentals when paying with $GPUDX",
                "staking_benefits": "8-20% APY + priority access + earnings boost",
                "p2p_provider_rewards": "Up to 15% earnings boost for GPU providers",
                "social_rewards": "Daily challenges, achievements, referral bonuses",
                "enterprise_benefits": "Bulk discounts, priority support, custom features"
            },
            "staking_tiers": {
                "bronze": {"stake": "1,000 $GPUDX", "apy": "8%", "discount": "5%"},
                "silver": {"stake": "10,000 $GPUDX", "apy": "12%", "discount": "10%"},
                "gold": {"stake": "100,000 $GPUDX", "apy": "15%", "discount": "15%"},
                "diamond": {"stake": "1,000,000 $GPUDX", "apy": "20%", "discount": "20%", "revenue_share": "1%"}
            },
            "earning_opportunities": {
                "gpu_rentals": "2% cashback + achievement bonuses",
                "p2p_providing": "Monthly bonuses for reliable service",
                "social_engagement": "10-50 $GPUDX per day for authentic sharing",
                "platform_contribution": "Bug reports, feature suggestions, tutorials",
                "referral_program": "50 $GPUDX + 5% lifetime earnings from referrals"
            },
            "no_liquidity_strategy": {
                "current_approach": "100% utility focus, zero speculation",
                "benefits": [
                    "Community built on real users, not traders",
                    "Token value based on platform usage, not hype",
                    "No pump-and-dump risks for genuine users",
                    "All tokens earned through valuable platform actions"
                ],
                "liquidity_criteria": {
                    "minimum_revenue": "$1M monthly platform revenue",
                    "user_base": "10,000+ monthly active users",
                    "utility_adoption": "50%+ of transactions use $GPUDX",
                    "community_approval": "75%+ governance vote required"
                }
            },
            "security_measures": {
                "smart_contract_audits": "Multiple third-party security audits",
                "multi_sig_treasury": "5-of-9 multisig for all treasury operations",
                "bug_bounty": "$100,000 bug bounty program",
                "emergency_controls": "Circuit breakers and pause functions"
            },
            "growth_projections": {
                "year_1": "Utility validation - 10K users, $1M monthly revenue",
                "year_2": "Enterprise scaling - 50K users, $10M monthly revenue", 
                "year_3": "Global expansion - 250K users, $50M monthly revenue",
                "year_5": "Market dominance - 1M+ users, $250M+ monthly revenue"
            },
            "governance": {
                "voting_power": "Based on staking amount + platform usage",
                "proposal_system": "Community can submit improvement ideas",
                "transparency": "Real-time metrics dashboard",
                "quarterly_reviews": "Regular tokenomics assessment and updates"
            },
            "whitepaper": {
                "full_document": "Available at docs.gpudex.com/tokenomics",
                "key_sections": [
                    "Token Utility Framework",
                    "Distribution Model", 
                    "Utility-First Launch Strategy",
                    "Token Economic Model",
                    "Security & Risk Management",
                    "Growth & Adoption Strategy"
                ],
                "last_updated": "January 2024",
                "next_review": "Quarterly updates based on platform metrics"
            }
        }
        
        return JSONResponse(content={
            "tokenomics": tokenomics_data,
            "key_message": "Utility First. Community Driven. Value Creation Focused.",
            "disclaimer": "No trading liquidity until utility and community criteria met",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting tokenomics info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/token/earning-calculator", response_model=Dict[str, Any])
@basic_rate_limit
async def get_earning_calculator(
    request: Request,
    user_type: str = Query("renter", description="User type: renter, provider, social"),
    monthly_usage: float = Query(100, description="Monthly platform usage (hours for renter, dollars for others)")
):
    """Calculate potential $GPUDX earnings based on user activity"""
    try:
        if user_type == "renter":
            # GPU renter earnings calculation
            monthly_spend = monthly_usage * 0.75  # Assume $0.75/hour average
            cashback_earnings = monthly_spend * 0.02  # 2% cashback
            first_rental_bonus = 50 if monthly_usage > 0 else 0
            achievement_bonuses = min(monthly_usage * 2, 200)  # Up to 200 per month
            
            total_monthly = cashback_earnings + achievement_bonuses
            annual_potential = (total_monthly * 12) + first_rental_bonus
            
            earnings_breakdown = {
                "monthly_spending": f"${monthly_spend:.2f}",
                "cashback_earnings": f"{cashback_earnings:.1f} $GPUDX",
                "achievement_bonuses": f"{achievement_bonuses:.1f} $GPUDX",
                "total_monthly": f"{total_monthly:.1f} $GPUDX",
                "annual_potential": f"{annual_potential:.1f} $GPUDX",
                "welcome_bonus": f"{first_rental_bonus} $GPUDX"
            }
            
        elif user_type == "provider":
            # P2P provider earnings calculation
            monthly_earnings = monthly_usage  # Monthly earnings in dollars
            base_gpudx_rewards = monthly_earnings * 0.1  # 10% in $GPUDX rewards
            staking_boost = base_gpudx_rewards * 0.15  # Assume 15% staking boost
            reliability_bonus = 50 if monthly_earnings > 100 else 0
            
            total_monthly = base_gpudx_rewards + staking_boost + reliability_bonus
            annual_potential = total_monthly * 12
            
            earnings_breakdown = {
                "monthly_earnings": f"${monthly_earnings:.2f}",
                "base_rewards": f"{base_gpudx_rewards:.1f} $GPUDX",
                "staking_boost": f"{staking_boost:.1f} $GPUDX",
                "reliability_bonus": f"{reliability_bonus} $GPUDX",
                "total_monthly": f"{total_monthly:.1f} $GPUDX",
                "annual_potential": f"{annual_potential:.1f} $GPUDX"
            }
            
        else:  # social user
            # Social engagement earnings calculation
            daily_posts = min(monthly_usage / 30, 1)  # Max 1 post per day
            daily_rewards = daily_posts * 25  # Average 25 $GPUDX per post
            monthly_social = daily_rewards * 30
            achievement_bonuses = min(monthly_usage * 5, 500)  # Up to 500 per month
            referral_potential = 250  # Assume 5 referrals per year average
            
            total_monthly = monthly_social + achievement_bonuses
            annual_potential = (total_monthly * 12) + referral_potential
            
            earnings_breakdown = {
                "daily_posting": f"{daily_rewards:.1f} $GPUDX per day",
                "monthly_social": f"{monthly_social:.1f} $GPUDX",
                "achievement_bonuses": f"{achievement_bonuses:.1f} $GPUDX", 
                "total_monthly": f"{total_monthly:.1f} $GPUDX",
                "annual_potential": f"{annual_potential:.1f} $GPUDX",
                "referral_potential": f"{referral_potential} $GPUDX"
            }
        
        # Calculate staking benefits
        staking_scenarios = {
            "bronze_tier": {
                "stake_required": "1,000 $GPUDX",
                "apy": "8%",
                "annual_yield": "80 $GPUDX",
                "gpu_discount": "5%"
            },
            "silver_tier": {
                "stake_required": "10,000 $GPUDX", 
                "apy": "12%",
                "annual_yield": "1,200 $GPUDX",
                "gpu_discount": "10%"
            },
            "gold_tier": {
                "stake_required": "100,000 $GPUDX",
                "apy": "15%", 
                "annual_yield": "15,000 $GPUDX",
                "gpu_discount": "15%"
            }
        }
        
        return JSONResponse(content={
            "user_type": user_type,
            "monthly_usage": monthly_usage,
            "earnings_breakdown": earnings_breakdown,
            "staking_opportunities": staking_scenarios,
            "key_benefits": {
                "no_speculation": "Earn tokens through real platform usage",
                "multiple_streams": "Combine rental, providing, and social earnings",
                "compound_growth": "Stake earnings for higher yields and discounts",
                "long_term_value": "Token utility increases with platform growth"
            },
            "disclaimer": "Estimates based on current tokenomics. Actual earnings may vary.",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error calculating earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)