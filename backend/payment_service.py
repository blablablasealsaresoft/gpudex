"""
GPUDex Payment Service
Comprehensive Stripe integration for subscription management and premium features.
"""

import stripe
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, validator
from fastapi import HTTPException, status
import json

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

Base = declarative_base()

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    UNPAID = "unpaid"

class PlanType(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    stripe_customer_id = Column(String(255), nullable=False, index=True)
    plan_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    trial_start = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime(timezone=True))
    api_limit_daily = Column(Integer, default=100)
    api_limit_monthly = Column(Integer, default=1000)
    price_per_month = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    subscription_metadata = Column(Text)  # JSON string for additional data

class PaymentIntentLog(Base):
    __tablename__ = "payment_intent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    stripe_payment_intent_id = Column(String(255), unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="usd")
    status = Column(String(50), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    payment_metadata = Column(Text)

# Pydantic models
class CreateCheckoutSessionRequest(BaseModel):
    plan_type: PlanType
    success_url: str
    cancel_url: str
    user_email: str
    user_id: int

class StripeWebhookEvent(BaseModel):
    type: str
    data: Dict[str, Any]

class StripeService:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        # Plan configurations
        self.plans = {
            PlanType.FREE: {
                "name": "Free",
                "price": 0,
                "api_limit_daily": 100,
                "api_limit_monthly": 1000,
                "features": ["Basic GPU price comparison", "100 API calls/day", "Email alerts"]
            },
            PlanType.BASIC: {
                "name": "Basic",
                "price": 29,  # $29/month
                "stripe_price_id": os.getenv("STRIPE_BASIC_PRICE_ID"),
                "api_limit_daily": 1000,
                "api_limit_monthly": 20000,
                "features": ["Everything in Free", "1,000 API calls/day", "Advanced filtering", "Price history"]
            },
            PlanType.PREMIUM: {
                "name": "Premium",
                "price": 79,  # $79/month
                "stripe_price_id": os.getenv("STRIPE_PREMIUM_PRICE_ID"),
                "api_limit_daily": 5000,
                "api_limit_monthly": 100000,
                "features": ["Everything in Basic", "5,000 API calls/day", "Arbitrage detection", "ML predictions", "Priority support"]
            },
            PlanType.ENTERPRISE: {
                "name": "Enterprise",
                "price": 299,  # $299/month
                "stripe_price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID"),
                "api_limit_daily": 50000,
                "api_limit_monthly": 1000000,
                "features": ["Everything in Premium", "50,000 API calls/day", "Custom integrations", "Dedicated support", "SLA"]
            }
        }
        
        # Initialize database
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        logger.info("Stripe service initialized successfully")

    def get_db(self) -> Session:
        """Get database session"""
        db = self.SessionLocal()
        try:
            return db
        finally:
            pass  # Session will be closed by caller

    async def create_checkout_session(self, request: CreateCheckoutSessionRequest) -> Dict[str, Any]:
        """Create Stripe checkout session for subscription"""
        try:
            plan_config = self.plans.get(request.plan_type)
            if not plan_config or request.plan_type == PlanType.FREE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid plan type for checkout"
                )

            # Create or get Stripe customer
            customer = await self._get_or_create_customer(request.user_email, request.user_id)
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan_config["stripe_price_id"],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.cancel_url,
                metadata={
                    'user_id': str(request.user_id),
                    'plan_type': request.plan_type,
                }
            )

            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id,
                "customer_id": customer.id
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment processing error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create checkout session"
            )

    async def _get_or_create_customer(self, email: str, user_id: int) -> stripe.Customer:
        """Get existing Stripe customer or create new one"""
        # Check if customer already exists
        customers = stripe.Customer.list(email=email, limit=1)
        
        if customers.data:
            return customers.data[0]
        
        # Create new customer
        customer = stripe.Customer.create(
            email=email,
            metadata={'user_id': str(user_id)}
        )
        
        return customer

    async def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            event_type = event_data.get('type')
            logger.info(f"Processing Stripe webhook event: {event_type}")

            if event_type.startswith('customer.subscription.'):
                return await self.process_subscription_event(event_data)
            elif event_type.startswith('payment_intent.'):
                return await self.process_payment_intent_event(event_data)
            elif event_type == 'checkout.session.completed':
                return await self.process_checkout_completed(event_data)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return {"status": "ignored", "event_type": event_type}

        except Exception as e:
            logger.error(f"Error processing webhook event: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook processing failed"
            )

    async def process_subscription_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process subscription-related webhook events"""
        db = self.get_db()
        try:
            event_type = event_data['type']
            subscription_data = event_data['data']['object']
            
            user_id = int(subscription_data['metadata'].get('user_id', 0))
            if not user_id:
                logger.warning("No user_id in subscription metadata")
                return {"status": "error", "message": "No user_id found"}

            # Get or create subscription record
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_data['id']
            ).first()

            if not subscription:
                # Create new subscription record
                plan_type = subscription_data['metadata'].get('plan_type', 'basic')
                plan_config = self.plans.get(plan_type, self.plans[PlanType.BASIC])
                
                subscription = Subscription(
                    user_id=user_id,
                    stripe_subscription_id=subscription_data['id'],
                    stripe_customer_id=subscription_data['customer'],
                    plan_type=plan_type,
                    status=subscription_data['status'],
                    api_limit_daily=plan_config['api_limit_daily'],
                    api_limit_monthly=plan_config['api_limit_monthly'],
                    price_per_month=plan_config['price']
                )
                db.add(subscription)
            
            # Update subscription details
            subscription.status = subscription_data['status']
            subscription.current_period_start = datetime.fromtimestamp(
                subscription_data['current_period_start'], tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                subscription_data['current_period_end'], tz=timezone.utc
            )
            subscription.cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
            
            if subscription_data.get('canceled_at'):
                subscription.canceled_at = datetime.fromtimestamp(
                    subscription_data['canceled_at'], tz=timezone.utc
                )
            
            subscription.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            
            # Update user premium status
            await self.update_user_premium_status(user_id, subscription.status == SubscriptionStatus.ACTIVE)
            
            logger.info(f"Updated subscription for user {user_id}: {event_type}")
            return {"status": "success", "user_id": user_id, "event_type": event_type}

        finally:
            db.close()

    async def process_payment_intent_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment intent webhook events"""
        db = self.get_db()
        try:
            payment_intent = event_data['data']['object']
            user_id = int(payment_intent['metadata'].get('user_id', 0))
            
            if not user_id:
                logger.warning("No user_id in payment intent metadata")
                return {"status": "error", "message": "No user_id found"}

            # Log payment intent
            payment_log = PaymentIntentLog(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent['id'],
                amount=payment_intent['amount'] / 100,  # Convert from cents
                currency=payment_intent['currency'],
                status=payment_intent['status'],
                description=payment_intent.get('description', ''),
                payment_metadata=json.dumps(payment_intent.get('metadata', {}))
            )
            
            db.add(payment_log)
            db.commit()
            
            logger.info(f"Logged payment intent for user {user_id}: {payment_intent['status']}")
            return {"status": "success", "user_id": user_id}

        finally:
            db.close()

    async def process_checkout_completed(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process completed checkout session"""
        session = event_data['data']['object']
        user_id = int(session['metadata'].get('user_id', 0))
        
        if session['mode'] == 'subscription':
            logger.info(f"Checkout completed for user {user_id} - subscription will be handled by subscription events")
        
        return {"status": "success", "user_id": user_id}

    async def get_customer_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create customer portal session for subscription management"""
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return portal_session.url
        except stripe.error.StripeError as e:
            logger.error(f"Error creating customer portal session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create portal session"
            )

    async def get_subscription_details(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get subscription details for a user"""
        db = self.get_db()
        try:
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).order_by(Subscription.created_at.desc()).first()
            
            if not subscription:
                return None
            
            plan_config = self.plans.get(subscription.plan_type, {})
            
            return {
                "subscription_id": subscription.stripe_subscription_id,
                "customer_id": subscription.stripe_customer_id,
                "plan_type": subscription.plan_type,
                "plan_name": plan_config.get("name", subscription.plan_type),
                "status": subscription.status,
                "price_per_month": subscription.price_per_month,
                "api_limit_daily": subscription.api_limit_daily,
                "api_limit_monthly": subscription.api_limit_monthly,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": subscription.canceled_at.isoformat() if subscription.canceled_at else None,
                "features": plan_config.get("features", [])
            }
        
        finally:
            db.close()

    async def cancel_subscription(self, user_id: int, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel user subscription"""
        db = self.get_db()
        try:
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE
            ).first()
            
            if not subscription:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No active subscription found"
                )
            
            # Cancel subscription in Stripe
            stripe_subscription = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=at_period_end
            )
            
            # Update local record
            subscription.cancel_at_period_end = at_period_end
            if not at_period_end:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.now(timezone.utc)
            
            db.commit()
            
            logger.info(f"Canceled subscription for user {user_id} (at_period_end: {at_period_end})")
            return {
                "status": "canceled",
                "cancel_at_period_end": at_period_end,
                "canceled_at": subscription.canceled_at.isoformat() if subscription.canceled_at else None
            }
        
        finally:
            db.close()

    async def update_user_premium_status(self, user_id: int, is_premium: bool):
        """Update user premium status in user table"""
        # This would update the user table - implementation depends on your user service
        # For now, we'll just log it
        logger.info(f"User {user_id} premium status updated to: {is_premium}")

    def get_plan_info(self, plan_type: PlanType) -> Dict[str, Any]:
        """Get plan information"""
        return self.plans.get(plan_type, {})

    def get_all_plans(self) -> Dict[str, Any]:
        """Get all available plans"""
        return {
            "plans": [
                {
                    "type": plan_type,
                    "name": config["name"],
                    "price": config["price"],
                    "api_limit_daily": config["api_limit_daily"],
                    "api_limit_monthly": config["api_limit_monthly"],
                    "features": config["features"]
                }
                for plan_type, config in self.plans.items()
            ]
        }

# Global Stripe service instance
stripe_service = StripeService() 