"""
Wallet Profile Service - User Dashboard & Analytics
Comprehensive wallet dashboard showing earnings, rentals, lendings, and activity
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine, JSON, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

Base = declarative_base()

class WalletProfile(Base):
    __tablename__ = "wallet_profiles"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True)
    email = Column(String(255))
    
    # Profile Info
    display_name = Column(String(100))
    bio = Column(Text)
    avatar_url = Column(String(500))
    location = Column(String(100))
    timezone = Column(String(50), default='UTC')
    
    # Account Status
    is_provider = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    reputation_score = Column(Float, default=0.0)  # 0-1000
    total_transactions = Column(Integer, default=0)
    
    # Lifetime Stats
    total_spent_usd = Column(Float, default=0.0)
    total_earned_usd = Column(Float, default=0.0)
    total_staked_gpudx = Column(Float, default=0.0)
    total_rewards_earned = Column(Float, default=0.0)
    
    # Activity
    first_transaction_date = Column(DateTime)
    last_active = Column(DateTime, default=datetime.utcnow)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Preferences
    preferred_currency = Column(String(10), default='USD')
    email_notifications = Column(Boolean, default=True)
    dashboard_settings = Column(JSON)  # Custom dashboard preferences

class WalletActivity(Base):
    __tablename__ = "wallet_activities"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), index=True, nullable=False)
    
    # Activity Details
    activity_type = Column(String(50), nullable=False)  # 'rental', 'lending', 'staking', 'reward', 'payment'
    amount_usd = Column(Float, default=0.0)
    amount_gpudx = Column(Float, default=0.0)
    
    # Transaction Info
    transaction_hash = Column(String(66))
    block_number = Column(Integer)
    gas_fee = Column(Float, default=0.0)
    
    # Related Items
    related_id = Column(Integer)  # ID of rental, listing, etc.
    related_type = Column(String(50))  # 'gpu_rental', 'gpu_listing', 'stake'
    
    # Metadata
    description = Column(Text)
    activity_metadata = Column(JSON)
    status = Column(String(20), default='completed')
    timestamp = Column(DateTime, default=datetime.utcnow)

class EarningsSummary(Base):
    __tablename__ = "earnings_summaries"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), index=True, nullable=False)
    
    # Time Period
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Earnings Breakdown
    provider_earnings_usd = Column(Float, default=0.0)
    provider_earnings_gpudx = Column(Float, default=0.0)
    staking_rewards_gpudx = Column(Float, default=0.0)
    referral_rewards_gpudx = Column(Float, default=0.0)
    total_earnings_usd = Column(Float, default=0.0)
    
    # Provider Stats (if applicable)
    hours_provided = Column(Float, default=0.0)
    rentals_completed = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    
    # Spending (if renter)
    total_spent_usd = Column(Float, default=0.0)
    hours_rented = Column(Float, default=0.0)
    
    created_date = Column(DateTime, default=datetime.utcnow)

class WalletProfileService:
    def __init__(self):
        self.db = self._initialize_database()
        logger.info("WalletProfileService initialized")
    
    def _initialize_database(self):
        """Initialize database connection"""
        database_url = os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        engine = create_engine(database_url)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    async def get_or_create_profile(self, wallet_address: str) -> Dict[str, Any]:
        """Get or create wallet profile"""
        try:
            profile = self.db.query(WalletProfile).filter(
                WalletProfile.wallet_address == wallet_address
            ).first()
            
            if not profile:
                profile = WalletProfile(
                    wallet_address=wallet_address,
                    display_name=f"User {wallet_address[:8]}...",
                    first_transaction_date=datetime.utcnow()
                )
                self.db.add(profile)
                self.db.commit()
            
            return {
                'wallet_address': profile.wallet_address,
                'username': profile.username,
                'display_name': profile.display_name,
                'bio': profile.bio,
                'avatar_url': profile.avatar_url,
                'location': profile.location,
                'is_provider': profile.is_provider,
                'is_verified': profile.is_verified,
                'reputation_score': profile.reputation_score,
                'total_transactions': profile.total_transactions,
                'member_since': profile.created_date.isoformat(),
                'last_active': profile.last_active.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return {'error': str(e)}
    
    async def update_profile(self, wallet_address: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update wallet profile"""
        try:
            profile = self.db.query(WalletProfile).filter(
                WalletProfile.wallet_address == wallet_address
            ).first()
            
            if not profile:
                return {'success': False, 'error': 'Profile not found'}
            
            # Update allowed fields
            allowed_fields = ['username', 'display_name', 'bio', 'avatar_url', 'location', 'timezone', 'email']
            for field in allowed_fields:
                if field in profile_data:
                    setattr(profile, field, profile_data[field])
            
            profile.last_active = datetime.utcnow()
            self.db.commit()
            
            return {'success': True, 'message': 'Profile updated successfully'}
            
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def get_dashboard_overview(self, wallet_address: str) -> Dict[str, Any]:
        """Get comprehensive dashboard overview"""
        try:
            # Get profile
            profile = await self.get_or_create_profile(wallet_address)
            
            # Get recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_activities = self.db.query(WalletActivity).filter(
                WalletActivity.wallet_address == wallet_address,
                WalletActivity.timestamp >= thirty_days_ago
            ).order_by(WalletActivity.timestamp.desc()).limit(20).all()
            
            # Calculate summary stats
            total_spent = sum(a.amount_usd for a in recent_activities if a.activity_type in ['rental', 'payment'])
            total_earned = sum(a.amount_usd for a in recent_activities if a.activity_type in ['lending', 'reward'])
            
            # Get current month earnings
            start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_summary = self.db.query(EarningsSummary).filter(
                EarningsSummary.wallet_address == wallet_address,
                EarningsSummary.period_start >= start_of_month,
                EarningsSummary.period_type == 'monthly'
            ).first()
            
            return {
                'profile': profile,
                'summary_stats': {
                    'total_spent_30d': total_spent,
                    'total_earned_30d': total_earned,
                    'net_profit_30d': total_earned - total_spent,
                    'total_transactions_30d': len(recent_activities),
                    'monthly_earnings': monthly_summary.total_earnings_usd if monthly_summary else 0.0,
                    'is_profitable': total_earned > total_spent
                },
                'recent_activities': [
                    {
                        'id': activity.id,
                        'type': activity.activity_type,
                        'amount_usd': activity.amount_usd,
                        'amount_gpudx': activity.amount_gpudx,
                        'description': activity.description,
                        'status': activity.status,
                        'timestamp': activity.timestamp.isoformat(),
                        'transaction_hash': activity.transaction_hash
                    } for activity in recent_activities
                ],
                'quick_actions': self._get_quick_actions(wallet_address)
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard overview: {e}")
            return {'error': str(e)}
    
    def _get_quick_actions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get suggested quick actions for user"""
        # This would be more sophisticated in production
        return [
            {
                'title': 'Rent GPU',
                'description': 'Find the best GPU for your needs',
                'action': 'navigate_to_marketplace',
                'icon': '🎮'
            },
            {
                'title': 'Become Provider',
                'description': 'Start earning with your GPU',
                'action': 'register_as_provider',
                'icon': '💰'
            },
            {
                'title': 'Stake $GPUDX',
                'description': 'Earn up to 20% APY',
                'action': 'stake_tokens',
                'icon': '🏆'
            },
            {
                'title': 'View Analytics',
                'description': 'Deep dive into your stats',
                'action': 'view_analytics',
                'icon': '📊'
            }
        ]
    
    async def get_earnings_breakdown(self, wallet_address: str, period: str = '30d') -> Dict[str, Any]:
        """Get detailed earnings breakdown"""
        try:
            if period == '30d':
                start_date = datetime.utcnow() - timedelta(days=30)
            elif period == '7d':
                start_date = datetime.utcnow() - timedelta(days=7)
            elif period == '1y':
                start_date = datetime.utcnow() - timedelta(days=365)
            else:
                start_date = datetime.utcnow() - timedelta(days=30)
            
            # Get earnings activities
            earnings = self.db.query(WalletActivity).filter(
                WalletActivity.wallet_address == wallet_address,
                WalletActivity.activity_type.in_(['lending', 'reward', 'staking']),
                WalletActivity.timestamp >= start_date
            ).all()
            
            # Get spending activities  
            spendings = self.db.query(WalletActivity).filter(
                WalletActivity.wallet_address == wallet_address,
                WalletActivity.activity_type.in_(['rental', 'payment']),
                WalletActivity.timestamp >= start_date
            ).all()
            
            # Categorize earnings
            provider_earnings = sum(e.amount_usd for e in earnings if e.activity_type == 'lending')
            staking_rewards = sum(e.amount_usd for e in earnings if e.activity_type == 'staking')
            other_rewards = sum(e.amount_usd for e in earnings if e.activity_type == 'reward')
            
            total_earnings = provider_earnings + staking_rewards + other_rewards
            total_spending = sum(s.amount_usd for s in spendings)
            
            return {
                'period': period,
                'earnings_breakdown': {
                    'provider_earnings': provider_earnings,
                    'staking_rewards': staking_rewards,
                    'other_rewards': other_rewards,
                    'total_earnings': total_earnings
                },
                'spending_breakdown': {
                    'gpu_rentals': sum(s.amount_usd for s in spendings if s.activity_type == 'rental'),
                    'platform_fees': sum(s.amount_usd for s in spendings if s.activity_type == 'payment'),
                    'total_spending': total_spending
                },
                'net_profit': total_earnings - total_spending,
                'roi_percentage': ((total_earnings - total_spending) / max(total_spending, 1)) * 100,
                'transaction_count': len(earnings) + len(spendings)
            }
            
        except Exception as e:
            logger.error(f"Error getting earnings breakdown: {e}")
            return {'error': str(e)}
    
    async def get_rental_history(self, wallet_address: str, limit: int = 50) -> Dict[str, Any]:
        """Get rental history (both as renter and provider)"""
        try:
            # Get rental activities
            rentals = self.db.query(WalletActivity).filter(
                WalletActivity.wallet_address == wallet_address,
                WalletActivity.activity_type.in_(['rental', 'lending'])
            ).order_by(WalletActivity.timestamp.desc()).limit(limit).all()
            
            rental_history = []
            for rental in rentals:
                rental_history.append({
                    'id': rental.id,
                    'type': 'rented' if rental.activity_type == 'rental' else 'provided',
                    'amount_usd': rental.amount_usd,
                    'amount_gpudx': rental.amount_gpudx,
                    'description': rental.description,
                    'status': rental.status,
                    'timestamp': rental.timestamp.isoformat(),
                    'transaction_hash': rental.transaction_hash,
                    'metadata': rental.activity_metadata
                })
            
            # Summary stats
            rentals_as_renter = [r for r in rentals if r.activity_type == 'rental']
            rentals_as_provider = [r for r in rentals if r.activity_type == 'lending']
            
            return {
                'rental_history': rental_history,
                'summary': {
                    'total_rentals': len(rentals),
                    'as_renter': len(rentals_as_renter),
                    'as_provider': len(rentals_as_provider),
                    'total_spent': sum(r.amount_usd for r in rentals_as_renter),
                    'total_earned': sum(r.amount_usd for r in rentals_as_provider),
                    'average_rental_cost': sum(r.amount_usd for r in rentals_as_renter) / max(len(rentals_as_renter), 1),
                    'average_earning_per_rental': sum(r.amount_usd for r in rentals_as_provider) / max(len(rentals_as_provider), 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting rental history: {e}")
            return {'error': str(e)}
    
    async def record_activity(self, wallet_address: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a new wallet activity"""
        try:
            activity = WalletActivity(
                wallet_address=wallet_address,
                activity_type=activity_data['activity_type'],
                amount_usd=activity_data.get('amount_usd', 0.0),
                amount_gpudx=activity_data.get('amount_gpudx', 0.0),
                description=activity_data.get('description', ''),
                related_id=activity_data.get('related_id'),
                related_type=activity_data.get('related_type'),
                activity_metadata=activity_data.get('metadata', {}),
                transaction_hash=activity_data.get('transaction_hash'),
                status=activity_data.get('status', 'completed')
            )
            
            self.db.add(activity)
            
            # Update profile stats
            profile = self.db.query(WalletProfile).filter(
                WalletProfile.wallet_address == wallet_address
            ).first()
            
            if profile:
                profile.total_transactions += 1
                profile.last_active = datetime.utcnow()
                
                if activity_data['activity_type'] in ['rental', 'payment']:
                    profile.total_spent_usd += activity_data.get('amount_usd', 0.0)
                elif activity_data['activity_type'] in ['lending', 'reward']:
                    profile.total_earned_usd += activity_data.get('amount_usd', 0.0)
            
            self.db.commit()
            
            return {'success': True, 'activity_id': activity.id}
            
        except Exception as e:
            logger.error(f"Error recording activity: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}

# Initialize wallet profile service
wallet_service = WalletProfileService() 