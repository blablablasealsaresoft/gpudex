# GPU Price Aggregator - Backend Foundation
# Run this to start collecting real pricing data

import logging
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import time

# Import our services
from database import DatabaseManager
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
from ml_prediction_service import ml_service, start_ml_service
from crypto_payment_service import (
    crypto_service, create_crypto_payment, get_crypto_payment_status, 
    get_supported_cryptocurrencies, CryptoPaymentRequest, CryptoPaymentResponse
)

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
    
    # Start background services
    start_alert_service()
    start_monitoring()
    start_ml_service()
    
    # Initialize database (tables are already created by services)
    
    # Load ML models if available
    try:
        await ml_service.load_models()
        logger.info("ML models loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load ML models: {e}")
    
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
            "Price predictions with ML",
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
    region: Optional[str] = Query(None, description="Filter by region"),
    include_predictions: bool = Query(False, description="Include ML price predictions")
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
            
            # Add predictions if requested
            predictions = {}
            if include_predictions and prices_dict:
                for price in prices_dict[:5]:  # Limit to top 5 for performance
                    pred = await ml_service.predict_price(
                        price["gpu_type"], 
                        price["provider"], 
                        "24h"
                    )
                    if pred:
                        predictions[f"{price['provider']}_{price['gpu_type']}"] = {
                            "predicted_price": pred.predicted_price,
                            "trend": pred.trend,
                            "confidence": pred.confidence_score
                        }
            
            response_time = time.time() - start_time
            monitoring_service.record_request("GET", "/api/v1/prices", 200, response_time)
            
            response = {
                "prices": prices_dict,
                "total_results": len(prices_dict),
                "arbitrage_opportunities": arbitrage_opportunities,
                "response_time_ms": round(response_time * 1000, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            if predictions:
                response["predictions"] = predictions
            
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

# ML Prediction endpoints
@app.get("/api/v1/predictions/{gpu_type}", response_model=Dict[str, Any])
@premium_rate_limit
async def get_price_predictions(
    request: Request,
    gpu_type: str,
    provider: Optional[str] = Query(None),
    horizon: str = Query("24h", description="Prediction horizon: 1h, 24h, 7d, 30d"),
    api_key: str = Depends(require_api_key)
):
    """Get ML-based price predictions"""
    try:
        if provider:
            # Single provider prediction
            prediction = await ml_service.predict_price(gpu_type, provider, horizon)
            if not prediction:
                raise HTTPException(status_code=404, detail="Prediction not available")
            
            result = {
                "gpu_type": prediction.gpu_type,
                "provider": prediction.provider,
                "current_price": prediction.current_price,
                "predicted_price": prediction.predicted_price,
                "confidence_score": prediction.confidence_score,
                "trend": prediction.trend,
                "horizon": prediction.prediction_horizon,
                "factors": prediction.factors,
                "timestamp": prediction.timestamp.isoformat()
            }
        else:
            # Multi-provider predictions
            providers = ["vast", "runpod", "lambda", "aws", "gcp"]
            predictions = []
            
            for prov in providers:
                pred = await ml_service.predict_price(gpu_type, prov, horizon)
                if pred:
                    predictions.append({
                        "provider": pred.provider,
                        "current_price": pred.current_price,
                        "predicted_price": pred.predicted_price,
                        "confidence_score": pred.confidence_score,
                        "trend": pred.trend
                    })
            
            result = {
                "gpu_type": gpu_type,
                "horizon": horizon,
                "predictions": predictions,
                "timestamp": datetime.now().isoformat()
            }
        
        return add_rate_limit_headers(JSONResponse(content=result), api_key)
        
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market-trends/{gpu_type}", response_model=Dict[str, Any])
@premium_rate_limit
async def get_market_trends(
    request: Request,
    gpu_type: str,
    api_key: str = Depends(require_api_key)
):
    """Get market trend analysis for specific GPU"""
    try:
        trend = await ml_service.analyze_market_trends(gpu_type)
        if not trend:
            raise HTTPException(status_code=404, detail="Trend analysis not available")
        
        result = {
            "gpu_type": trend.gpu_type,
            "trend_direction": trend.trend_direction,
            "strength": trend.strength,
            "volatility": trend.volatility,
            "support_level": trend.support_level,
            "resistance_level": trend.resistance_level,
            "moving_average_7d": trend.moving_average_7d,
            "moving_average_30d": trend.moving_average_30d,
            "timestamp": datetime.now().isoformat()
        }
        
        return add_rate_limit_headers(JSONResponse(content=result), api_key)
        
    except Exception as e:
        logger.error(f"Error getting market trends: {e}")
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
        
        # Apply crypto discount
        discount_applied = 0
        if rental_request.payment_method == 'crypto':
            discount_applied = total_cost * 0.01  # 1% crypto discount
        
        final_cost = total_cost - discount_applied
        
        # Generate rental ID
        import uuid
        rental_id = f"rental_{uuid.uuid4().hex[:12]}"
        
        # Store rental in database (simplified for now)
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
            "status": "pending_payment",
            "created_at": datetime.now(),
            "expires_at": datetime.now().replace(hour=23, minute=59, second=59)
        }
        
        # TODO: Store in actual database
        logger.info(f"Created rental: {rental_id} for {rental_request.user_email}")
        
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
    """Get rental status and connection details"""
    try:
        # TODO: Get from actual database
        # For now, return simulated data
        return {
            "rental_id": rental_id,
            "status": "active",
            "connection_details": {
                "ssh_host": f"gpu-{rental_id[:8]}.gpudex.ai",
                "ssh_port": 22,
                "username": "gpudex",
                "password": f"temp_{rental_id[:8]}",
                "jupyter_url": f"https://jupyter-{rental_id[:8]}.gpudex.ai",
                "vscode_url": f"https://vscode-{rental_id[:8]}.gpudex.ai"
            },
            "remaining_hours": 23.5,
            "gpu_info": {
                "gpu_type": "RTX 4090",
                "memory": "24GB",
                "cuda_version": "12.2",
                "driver_version": "535.86"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting rental status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rental status")

@app.post("/api/v1/rentals/{rental_id}/payment")
@basic_rate_limit
async def process_rental_payment(
    request: Request,
    rental_id: str,
    payment_data: Dict[str, Any]
):
    """Process payment for GPU rental"""
    try:
        # TODO: Process actual payment based on method
        payment_method = payment_data.get("payment_method")
        
        if payment_method == "crypto":
            # Create crypto payment
            crypto_payment = await create_crypto_payment(CryptoPaymentRequest(
                amount_usd=payment_data["amount"],
                cryptocurrency=payment_data["cryptocurrency"],
                user_email=payment_data["user_email"],
                order_description=f"GPU Rental {rental_id}",
                gpu_booking_details={
                    "rental_id": rental_id,
                    "gpu_type": payment_data.get("gpu_type"),
                    "hours": payment_data.get("hours")
                }
            ))
            
            return {
                "payment_id": crypto_payment.payment_id,
                "payment_url": crypto_payment.payment_url,
                "wallet_address": crypto_payment.wallet_address,
                "amount": crypto_payment.payment_amount,
                "cryptocurrency": crypto_payment.cryptocurrency
            }
        
        elif payment_method == "stripe":
            # TODO: Implement Stripe payment
            return {"message": "Stripe payment not yet implemented"}
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported payment method")
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        log_level="info"
    )