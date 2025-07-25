"""
GPUDex Payment Service
Comprehensive Stripe integration for subscription management and premium features.
"""

import os
import json
import stripe
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, Enum
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import DatabaseManager
import enum

logger = logging.getLogger(__name__)

# Stripe Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"

class PlanType(enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

# Database Models
class Subscription(DatabaseManager.Base):
    """User subscription model."""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Stripe data
    stripe_customer_id = Column(String(255), nullable=False, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_price_id = Column(String(255), nullable=True)
    
    # Subscription details
    plan_type = Column(Enum(PlanType), default=PlanType.FREE)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    
    # Billing
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    
    # Usage tracking
    api_calls_used = Column(Integer, default=0)
    api_calls_limit = Column(Integer, default=100)  # Monthly limit
    
    # Metadata
    metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_type": self.plan_type.value if self.plan_type else None,
            "status": self.status.value if self.status else None,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "api_calls_used": self.api_calls_used,
            "api_calls_limit": self.api_calls_limit,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class PaymentHistory(DatabaseManager.Base):
    """Payment history tracking."""
    __tablename__ = "payment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    subscription_id = Column(Integer, nullable=True)
    
    # Stripe data
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    
    # Payment details
    amount = Column(Float, nullable=False)  # In dollars
    currency = Column(String(3), default="USD")
    status = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    # Metadata
    metadata = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Models
class CreateCheckoutSession(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

class CreatePortalSession(BaseModel):
    return_url: str

class UsageUpdate(BaseModel):
    api_calls_used: int

class PlanDetails(BaseModel):
    plan_type: str
    name: str
    description: str
    price: float
    currency: str
    interval: str
    features: List[str]
    api_calls_limit: int
    stripe_price_id: str

class PaymentService:
    """Comprehensive Stripe payment service."""
    
    # Plan configuration
    PLANS = {
        PlanType.FREE: {
            "name": "Free Tier",
            "description": "Perfect for getting started",
            "price": 0,
            "currency": "USD",
            "interval": "month",
            "features": [
                "100 API calls per month",
                "Basic GPU price data",
                "Standard support"
            ],
            "api_calls_limit": 100,
            "stripe_price_id": None
        },
        PlanType.BASIC: {
            "name": "Basic Plan",
            "description": "For small teams and individual developers",
            "price": 29,
            "currency": "USD", 
            "interval": "month",
            "features": [
                "1,000 API calls per month",
                "Real-time price updates",
                "Advanced filtering",
                "Email support"
            ],
            "api_calls_limit": 1000,
            "stripe_price_id": os.getenv("STRIPE_BASIC_PRICE_ID")
        },
        PlanType.PRO: {
            "name": "Pro Plan",
            "description": "For growing businesses and power users",
            "price": 99,
            "currency": "USD",
            "interval": "month", 
            "features": [
                "10,000 API calls per month",
                "Arbitrage detection",
                "Price predictions",
                "Custom alerts",
                "Priority support"
            ],
            "api_calls_limit": 10000,
            "stripe_price_id": os.getenv("STRIPE_PRO_PRICE_ID")
        },
        PlanType.ENTERPRISE: {
            "name": "Enterprise Plan",
            "description": "For large organizations with custom needs",
            "price": 299,
            "currency": "USD",
            "interval": "month",
            "features": [
                "Unlimited API calls",
                "Custom integrations",
                "Advanced analytics",
                "Dedicated support",
                "SLA guarantee"
            ],
            "api_calls_limit": 999999,
            "stripe_price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID")
        }
    }
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        # Create tables if they don't exist
        Subscription.__table__.create(self.db_manager.engine, checkfirst=True)
        PaymentHistory.__table__.create(self.db_manager.engine, checkfirst=True)
    
    def get_or_create_customer(self, user_id: int, email: str, name: str = None) -> str:
        """Get existing Stripe customer or create new one."""
        try:
            # Try to find existing subscription with customer ID
            db = self.db_manager.get_db()
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            
            if subscription and subscription.stripe_customer_id:
                # Verify customer exists in Stripe
                try:
                    customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
                    return customer.id
                except stripe.error.InvalidRequestError:
                    # Customer doesn't exist, create new one
                    pass
            
            # Create new customer
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )
            
            # Update or create subscription record
            if subscription:
                subscription.stripe_customer_id = customer.id
                subscription.updated_at = datetime.utcnow()
            else:
                subscription = Subscription(
                    user_id=user_id,
                    stripe_customer_id=customer.id
                )
                db.add(subscription)
            
            db.commit()
            db.close()
            
            logger.info(f"Created Stripe customer for user {user_id}: {customer.id}")
            return customer.id
            
        except Exception as e:
            logger.error(f"Error creating Stripe customer: {e}")
            raise
    
    def create_checkout_session(self, user_id: int, email: str, checkout_data: CreateCheckoutSession) -> Dict[str, Any]:
        """Create Stripe checkout session for subscription."""
        try:
            customer_id = self.get_or_create_customer(user_id, email)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': checkout_data.price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=checkout_data.success_url,
                cancel_url=checkout_data.cancel_url,
                metadata={
                    'user_id': user_id
                }
            )
            
            logger.info(f"Created checkout session for user {user_id}: {session.id}")
            
            return {
                "checkout_url": session.url,
                "session_id": session.id
            }
            
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise
    
    def create_customer_portal_session(self, user_id: int, portal_data: CreatePortalSession) -> Dict[str, Any]:
        """Create Stripe customer portal session."""
        try:
            db = self.db_manager.get_db()
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            db.close()
            
            if not subscription or not subscription.stripe_customer_id:
                raise ValueError("No subscription found for user")
            
            # Create portal session
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=portal_data.return_url,
            )
            
            return {
                "portal_url": session.url
            }
            
        except Exception as e:
            logger.error(f"Error creating portal session: {e}")
            raise
    
    def get_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user subscription details."""
        try:
            db = self.db_manager.get_db()
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            db.close()
            
            if not subscription:
                return None
            
            # Add plan details
            result = subscription.to_dict()
            if subscription.plan_type in self.PLANS:
                result["plan_details"] = self.PLANS[subscription.plan_type]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None
    
    def update_subscription_from_stripe(self, stripe_subscription: Dict[str, Any]) -> bool:
        """Update subscription from Stripe webhook data."""
        try:
            db = self.db_manager.get_db()
            
            # Find subscription by Stripe subscription ID
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_subscription["id"]
            ).first()
            
            if not subscription:
                # Find by customer ID and create subscription record
                customer_id = stripe_subscription["customer"]
                subscription = db.query(Subscription).filter(
                    Subscription.stripe_customer_id == customer_id
                ).first()
                
                if subscription:
                    subscription.stripe_subscription_id = stripe_subscription["id"]
            
            if not subscription:
                logger.warning(f"Subscription not found for Stripe subscription: {stripe_subscription['id']}")
                db.close()
                return False
            
            # Update subscription details
            subscription.status = SubscriptionStatus(stripe_subscription["status"])
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription["current_period_start"])
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription["current_period_end"])
            subscription.cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)
            
            # Determine plan type from price ID
            if stripe_subscription.get("items", {}).get("data"):
                price_id = stripe_subscription["items"]["data"][0]["price"]["id"]
                subscription.stripe_price_id = price_id
                
                # Map price ID to plan type
                for plan_type, plan_config in self.PLANS.items():
                    if plan_config.get("stripe_price_id") == price_id:
                        subscription.plan_type = plan_type
                        subscription.api_calls_limit = plan_config["api_calls_limit"]
                        break
            
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            db.close()
            
            logger.info(f"Updated subscription for user {subscription.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False
    
    def handle_payment_success(self, payment_intent: Dict[str, Any]) -> bool:
        """Handle successful payment."""
        try:
            db = self.db_manager.get_db()
            
            # Find user by customer ID
            customer_id = payment_intent["customer"]
            subscription = db.query(Subscription).filter(
                Subscription.stripe_customer_id == customer_id
            ).first()
            
            if not subscription:
                logger.warning(f"Subscription not found for customer: {customer_id}")
                db.close()
                return False
            
            # Create payment history record
            payment_record = PaymentHistory(
                user_id=subscription.user_id,
                subscription_id=subscription.id,
                stripe_payment_intent_id=payment_intent["id"],
                amount=payment_intent["amount"] / 100,  # Convert from cents
                currency=payment_intent["currency"].upper(),
                status=payment_intent["status"],
                description=payment_intent.get("description", "Subscription payment"),
                metadata=json.dumps(payment_intent.get("metadata", {}))
            )
            
            db.add(payment_record)
            db.commit()
            db.close()
            
            logger.info(f"Recorded payment for user {subscription.user_id}: ${payment_record.amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
            return False
    
    def update_usage(self, user_id: int, api_calls_used: int) -> bool:
        """Update API usage for user."""
        try:
            db = self.db_manager.get_db()
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            
            if not subscription:
                # Create default free subscription
                subscription = Subscription(
                    user_id=user_id,
                    plan_type=PlanType.FREE,
                    api_calls_limit=self.PLANS[PlanType.FREE]["api_calls_limit"]
                )
                db.add(subscription)
            
            subscription.api_calls_used = api_calls_used
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            db.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating usage: {e}")
            return False
    
    def check_api_limit(self, user_id: int) -> Dict[str, Any]:
        """Check if user has exceeded API limits."""
        try:
            db = self.db_manager.get_db()
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            db.close()
            
            if not subscription:
                # Default free tier limits
                return {
                    "allowed": True,
                    "calls_used": 0,
                    "calls_limit": self.PLANS[PlanType.FREE]["api_calls_limit"],
                    "plan_type": "free"
                }
            
            calls_used = subscription.api_calls_used or 0
            calls_limit = subscription.api_calls_limit or 100
            
            return {
                "allowed": calls_used < calls_limit,
                "calls_used": calls_used,
                "calls_limit": calls_limit,
                "plan_type": subscription.plan_type.value if subscription.plan_type else "free",
                "remaining": max(0, calls_limit - calls_used)
            }
            
        except Exception as e:
            logger.error(f"Error checking API limit: {e}")
            return {"allowed": False, "error": str(e)}
    
    def get_all_plans(self) -> List[Dict[str, Any]]:
        """Get all available subscription plans."""
        plans = []
        for plan_type, config in self.PLANS.items():
            plan_data = {
                "plan_type": plan_type.value,
                **config
            }
            plans.append(plan_data)
        
        return plans
    
    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process Stripe webhook."""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
            
            event_type = event["type"]
            event_data = event["data"]["object"]
            
            logger.info(f"Processing webhook: {event_type}")
            
            # Handle different event types
            if event_type == "customer.subscription.created":
                self.update_subscription_from_stripe(event_data)
            
            elif event_type == "customer.subscription.updated":
                self.update_subscription_from_stripe(event_data)
            
            elif event_type == "customer.subscription.deleted":
                # Handle subscription cancellation
                self.update_subscription_from_stripe(event_data)
            
            elif event_type == "payment_intent.succeeded":
                self.handle_payment_success(event_data)
            
            elif event_type == "invoice.payment_succeeded":
                # Handle successful recurring payment
                if event_data.get("subscription"):
                    # Get subscription details
                    subscription = stripe.Subscription.retrieve(event_data["subscription"])
                    self.update_subscription_from_stripe(subscription)
            
            elif event_type == "invoice.payment_failed":
                # Handle failed payment
                logger.warning(f"Payment failed for invoice: {event_data['id']}")
            
            return {"status": "success", "event_type": event_type}
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise ValueError("Invalid webhook signature")
        
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise

# Global payment service instance
payment_service = PaymentService() 