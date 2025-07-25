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
                    "price": price_data.price_per_hour,
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
            prices_dict.sort(key=lambda x: x["price"])
            
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
                    "price": price_data.price_per_hour,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        log_level="info"
    )