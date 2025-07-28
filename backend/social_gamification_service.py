"""
Social Media Gamification Service - Viral Growth Engine
Daily $GPUDX rewards for social media posting, streaks, achievements, and viral campaigns
"""

import os
import logging
import re
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
import asyncio
import aiohttp
from enum import Enum

logger = logging.getLogger(__name__)

Base = declarative_base()

class RewardType(Enum):
    DAILY_POST = "daily_post"
    STREAK_BONUS = "streak_bonus"
    VIRAL_BONUS = "viral_bonus"
    ACHIEVEMENT = "achievement"
    REFERRAL = "referral"
    CHALLENGE = "challenge"
    COMMUNITY_VOTE = "community_vote"

class SocialPlatform(Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    REDDIT = "reddit"
    DISCORD = "discord"
    TELEGRAM = "telegram"

@dataclass
class SocialReward:
    user_address: str
    reward_type: RewardType
    amount: float
    platform: SocialPlatform
    post_url: str
    timestamp: datetime
    bonus_multiplier: float = 1.0

@dataclass
class Achievement:
    achievement_id: str
    name: str
    description: str
    icon: str
    reward_amount: float
    rarity: str  # 'common', 'rare', 'epic', 'legendary'
    unlock_condition: str

class SocialProfile(Base):
    __tablename__ = "social_profiles"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), index=True, nullable=False)
    
    # Social Media Accounts
    twitter_username = Column(String(100))
    twitter_id = Column(String(100))
    linkedin_profile = Column(String(200))
    reddit_username = Column(String(100))
    discord_id = Column(String(100))
    telegram_username = Column(String(100))
    
    # Gamification Stats
    total_posts = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    total_rewards_earned = Column(Float, default=0.0)
    referrals_count = Column(Integer, default=0)
    
    # Achievement System
    achievements_unlocked = Column(JSON, default=list)  # List of achievement IDs
    achievement_points = Column(Integer, default=0)
    user_level = Column(Integer, default=1)
    experience_points = Column(Integer, default=0)
    
    # Leaderboard Rankings
    daily_rank = Column(Integer, default=0)
    weekly_rank = Column(Integer, default=0)
    monthly_rank = Column(Integer, default=0)
    all_time_rank = Column(Integer, default=0)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_date = Column(DateTime)
    
    # Activity Tracking
    last_post_date = Column(DateTime)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow)

class SocialPost(Base):
    __tablename__ = "social_posts"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), index=True, nullable=False)
    
    # Post Details
    platform = Column(String(20), nullable=False)
    post_id = Column(String(100), nullable=False)
    post_url = Column(String(500), nullable=False)
    post_content = Column(Text)
    
    # Engagement Metrics
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    views = Column(Integer, default=0)
    engagement_score = Column(Float, default=0.0)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    has_gpudex_tag = Column(Boolean, default=False)
    has_required_hashtags = Column(Boolean, default=False)
    
    # Rewards
    reward_amount = Column(Float, default=0.0)
    bonus_multiplier = Column(Float, default=1.0)
    is_rewarded = Column(Boolean, default=False)
    
    # Viral Tracking
    viral_score = Column(Float, default=0.0)
    is_viral = Column(Boolean, default=False)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime)

class DailyChallenge(Base):
    __tablename__ = "daily_challenges"
    
    id = Column(Integer, primary_key=True)
    
    # Challenge Details
    challenge_id = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    challenge_type = Column(String(50), nullable=False)  # 'content', 'engagement', 'referral', 'creative'
    
    # Requirements
    required_hashtags = Column(JSON)  # List of required hashtags
    required_mentions = Column(JSON)  # List of required mentions
    minimum_engagement = Column(Integer, default=0)
    target_platforms = Column(JSON)  # List of target platforms
    
    # Rewards
    base_reward = Column(Float, nullable=False)
    bonus_rewards = Column(JSON)  # Tiered bonus structure
    total_participants = Column(Integer, default=0)
    
    # Timing
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Leaderboard
    top_performers = Column(JSON, default=list)
    
    created_date = Column(DateTime, default=datetime.utcnow)

class SocialRewardHistory(Base):
    __tablename__ = "social_reward_history"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), index=True, nullable=False)
    
    # Reward Details
    reward_type = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    platform = Column(String(20), nullable=False)
    
    # Source
    post_id = Column(String(100))
    challenge_id = Column(String(50))
    achievement_id = Column(String(50))
    
    # Metadata
    bonus_multiplier = Column(Float, default=1.0)
    streak_count = Column(Integer, default=0)
    description = Column(Text)
    
    # Transaction
    transaction_hash = Column(String(66))
    is_distributed = Column(Boolean, default=False)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    distributed_date = Column(DateTime)

class SocialGamificationService:
    def __init__(self):
        self.db = self._initialize_database()
        
        # Reward configuration
        self.reward_config = {
            'daily_post': {
                'base_amount': 10.0,  # $GPUDX
                'max_daily': 50.0,
                'streak_multipliers': {
                    7: 1.5,   # 7-day streak: 1.5x
                    30: 2.0,  # 30-day streak: 2x
                    100: 3.0, # 100-day streak: 3x
                    365: 5.0  # 1-year streak: 5x
                }
            },
            'viral_bonus': {
                'thresholds': {
                    100: 25.0,   # 100 likes/shares
                    500: 100.0,  # 500 likes/shares
                    1000: 250.0, # 1K likes/shares
                    5000: 500.0, # 5K likes/shares
                    10000: 1000.0 # 10K likes/shares
                }
            },
            'referral': {
                'amount': 50.0,  # $GPUDX per successful referral
                'lifetime_bonus': 0.05  # 5% of referree's earnings forever
            }
        }
        
        # Achievement system
        self.achievements = self._initialize_achievements()
        
        # Fun challenges and campaigns
        self.daily_challenges = self._initialize_challenges()
        
        logger.info("SocialGamificationService initialized - Budget-friendly viral growth engine ready!")
    
    def _initialize_database(self):
        """Initialize database connection"""
        database_url = os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        engine = create_engine(database_url)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def _initialize_achievements(self) -> List[Achievement]:
        """Initialize the achievement system"""
        return [
            # Posting Achievements
            Achievement("first_post", "First Steps", "Made your first GPUDex post", "🚀", 25.0, "common", "post_count >= 1"),
            Achievement("social_rookie", "Social Rookie", "Posted 10 times", "📱", 50.0, "common", "post_count >= 10"),
            Achievement("content_creator", "Content Creator", "Posted 50 times", "✨", 150.0, "rare", "post_count >= 50"),
            Achievement("social_influencer", "Social Influencer", "Posted 200 times", "🌟", 500.0, "epic", "post_count >= 200"),
            Achievement("gpudex_evangelist", "GPUDex Evangelist", "Posted 500 times", "👑", 1000.0, "legendary", "post_count >= 500"),
            
            # Streak Achievements
            Achievement("week_warrior", "Week Warrior", "7-day posting streak", "🔥", 75.0, "common", "streak >= 7"),
            Achievement("month_master", "Month Master", "30-day posting streak", "💎", 300.0, "rare", "streak >= 30"),
            Achievement("quarter_champion", "Quarter Champion", "90-day posting streak", "🏆", 900.0, "epic", "streak >= 90"),
            Achievement("year_legend", "Year Legend", "365-day posting streak", "⚡", 3650.0, "legendary", "streak >= 365"),
            
            # Viral Achievements
            Achievement("viral_starter", "Viral Starter", "Post reached 100 likes", "📈", 100.0, "rare", "viral_post_100"),
            Achievement("viral_star", "Viral Star", "Post reached 1K likes", "🌟", 500.0, "epic", "viral_post_1000"),
            Achievement("viral_legend", "Viral Legend", "Post reached 10K likes", "🚀", 2500.0, "legendary", "viral_post_10000"),
            
            # Referral Achievements
            Achievement("recruiter", "Recruiter", "Referred 5 users", "🤝", 250.0, "rare", "referrals >= 5"),
            Achievement("ambassador", "Ambassador", "Referred 25 users", "🎯", 1250.0, "epic", "referrals >= 25"),
            Achievement("growth_hacker", "Growth Hacker", "Referred 100 users", "💰", 5000.0, "legendary", "referrals >= 100"),
            
            # Special Achievements
            Achievement("early_adopter", "Early Adopter", "Joined in the first month", "🎖️", 500.0, "epic", "early_user"),
            Achievement("whale_spotter", "Whale Spotter", "Staked 100K+ $GPUDX", "🐋", 1000.0, "epic", "staked >= 100000"),
            Achievement("diamond_hands", "Diamond Hands", "Held tokens for 1 year", "💎", 2000.0, "legendary", "holding_period >= 365"),
        ]
    
    def _initialize_challenges(self) -> List[Dict]:
        """Initialize fun daily challenges"""
        return [
            {
                "title": "GPU Meme Monday",
                "description": "Share your best GPU-related meme with #GPUMemeMonday",
                "type": "creative",
                "hashtags": ["#GPUMemeMonday", "#GPUDex"],
                "reward": 25.0,
                "bonus": "Most liked meme gets 100 $GPUDX bonus"
            },
            {
                "title": "Tech Tuesday",
                "description": "Share a cool tech fact or GPU benchmark with #TechTuesday",
                "type": "educational",
                "hashtags": ["#TechTuesday", "#GPUDex"],
                "reward": 20.0,
                "bonus": "Most informative post gets 75 $GPUDX bonus"
            },
            {
                "title": "Wisdom Wednesday",
                "description": "Share your best crypto/GPU trading tip with #WisdomWednesday",
                "type": "educational",
                "hashtags": ["#WisdomWednesday", "#GPUDex"],
                "reward": 20.0,
                "bonus": "Best tip gets 100 $GPUDX bonus"
            },
            {
                "title": "Throwback Thursday",
                "description": "Share your first GPU or mining rig photo with #ThrowbackThursday",
                "type": "nostalgic",
                "hashtags": ["#ThrowbackThursday", "#GPUDex"],
                "reward": 20.0,
                "bonus": "Most nostalgic post gets 75 $GPUDX bonus"
            },
            {
                "title": "Feature Friday",
                "description": "Showcase a GPUDex feature or share what you love about the platform",
                "type": "promotional",
                "hashtags": ["#FeatureFriday", "#GPUDex"],
                "reward": 30.0,
                "bonus": "Best showcase gets 150 $GPUDX bonus"
            },
            {
                "title": "Setup Saturday",
                "description": "Show off your GPU setup, rig, or workspace with #SetupSaturday",
                "type": "showcase",
                "hashtags": ["#SetupSaturday", "#GPUDex"],
                "reward": 25.0,
                "bonus": "Coolest setup gets 200 $GPUDX bonus"
            },
            {
                "title": "Success Sunday",
                "description": "Share your GPUDex success story or earnings milestone",
                "type": "testimonial",
                "hashtags": ["#SuccessSunday", "#GPUDex"],
                "reward": 35.0,
                "bonus": "Most inspiring story gets 250 $GPUDX bonus"
            }
        ]
    
    async def register_social_profile(self, wallet_address: str, social_data: Dict[str, str]) -> Dict[str, Any]:
        """Register user's social media profiles"""
        try:
            # Check if profile exists
            profile = self.db.query(SocialProfile).filter(
                SocialProfile.wallet_address == wallet_address
            ).first()
            
            if not profile:
                profile = SocialProfile(wallet_address=wallet_address)
                self.db.add(profile)
            
            # Update social media accounts
            if 'twitter_username' in social_data:
                profile.twitter_username = social_data['twitter_username']
            if 'linkedin_profile' in social_data:
                profile.linkedin_profile = social_data['linkedin_profile']
            if 'reddit_username' in social_data:
                profile.reddit_username = social_data['reddit_username']
            if 'discord_id' in social_data:
                profile.discord_id = social_data['discord_id']
            
            profile.updated_date = datetime.utcnow()
            self.db.commit()
            
            # Give welcome bonus
            await self._award_tokens(wallet_address, 50.0, RewardType.ACHIEVEMENT, "social_registration")
            
            return {
                'success': True,
                'message': 'Social profiles registered successfully',
                'welcome_bonus': 50.0,
                'daily_posting_info': self._get_daily_posting_info()
            }
            
        except Exception as e:
            logger.error(f"Error registering social profile: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def submit_daily_post(self, wallet_address: str, post_url: str, platform: str) -> Dict[str, Any]:
        """Submit a daily social media post for rewards"""
        try:
            # Verify the post
            verification_result = await self._verify_post(post_url, platform)
            
            if not verification_result['is_valid']:
                return {
                    'success': False,
                    'error': verification_result['error'],
                    'requirements': self._get_posting_requirements()
                }
            
            # Check if already posted today
            today = datetime.utcnow().date()
            existing_post = self.db.query(SocialPost).filter(
                SocialPost.wallet_address == wallet_address,
                SocialPost.created_date >= today,
                SocialPost.platform == platform
            ).first()
            
            if existing_post:
                return {
                    'success': False,
                    'error': 'Already posted on this platform today',
                    'next_post_time': (datetime.combine(today + timedelta(days=1), datetime.min.time())).isoformat()
                }
            
            # Create post record
            post = SocialPost(
                wallet_address=wallet_address,
                platform=platform,
                post_id=verification_result['post_id'],
                post_url=post_url,
                post_content=verification_result['content'],
                has_gpudex_tag=verification_result['has_gpudex_tag'],
                has_required_hashtags=verification_result['has_hashtags'],
                is_verified=True
            )
            self.db.add(post)
            
            # Update user profile
            profile = await self._get_or_create_profile(wallet_address)
            profile.total_posts += 1
            profile.last_post_date = datetime.utcnow()
            
            # Calculate streak
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            if profile.last_post_date and profile.last_post_date.date() == yesterday:
                profile.current_streak += 1
            else:
                profile.current_streak = 1
            
            if profile.current_streak > profile.longest_streak:
                profile.longest_streak = profile.current_streak
            
            # Calculate rewards
            reward_calculation = await self._calculate_rewards(profile, post, verification_result)
            
            # Award tokens
            await self._award_tokens(
                wallet_address, 
                reward_calculation['total_amount'], 
                RewardType.DAILY_POST,
                f"Daily post on {platform}"
            )
            
            # Check achievements
            new_achievements = await self._check_achievements(profile)
            
            # Update post with reward info
            post.reward_amount = reward_calculation['total_amount']
            post.bonus_multiplier = reward_calculation['multiplier']
            post.is_rewarded = True
            
            profile.total_rewards_earned += reward_calculation['total_amount']
            profile.updated_date = datetime.utcnow()
            
            self.db.commit()
            
            return {
                'success': True,
                'rewards': reward_calculation,
                'new_achievements': new_achievements,
                'streak': {
                    'current': profile.current_streak,
                    'longest': profile.longest_streak,
                    'next_milestone': self._get_next_streak_milestone(profile.current_streak)
                },
                'tomorrow_challenge': self._get_tomorrows_challenge(),
                'leaderboard_rank': await self._get_user_rank(wallet_address, 'daily')
            }
            
        except Exception as e:
            logger.error(f"Error submitting daily post: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def _verify_post(self, post_url: str, platform: str) -> Dict[str, Any]:
        """Verify social media post meets requirements (Budget-friendly verification)"""
        try:
            # Simple URL validation and basic verification
            if not post_url.startswith(('http://', 'https://')):
                return {'is_valid': False, 'error': 'Invalid URL format'}
            
            # Extract post ID from URL
            post_id = self._extract_post_id(post_url, platform)
            
            # Honor system verification (users self-report requirements)
            # In future versions, could add screenshot verification or community voting
            return {
                'is_valid': True,
                'post_id': post_id,
                'content': f'User-submitted post on {platform} about GPUDex',
                'has_gpudex_tag': True,  # Honor system - users confirm they mentioned @GPUDex
                'has_hashtags': True,    # Honor system - users confirm they used hashtags
                'likes': 0,              # Manual entry or future API integration
                'shares': 0,             # Manual entry or future API integration
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error verifying post: {e}")
            return {'is_valid': False, 'error': 'Verification failed'}
    
    def _extract_post_id(self, post_url: str, platform: str) -> str:
        """Extract post ID from URL for different platforms"""
        try:
            if 'twitter.com' in post_url or 'x.com' in post_url:
                # Extract tweet ID from Twitter/X URL
                match = re.search(r'/status/(\d+)', post_url)
                if match:
                    return match.group(1)
            elif 'linkedin.com' in post_url:
                # Extract LinkedIn post ID
                match = re.search(r'/activity-(\d+)-', post_url)
                if match:
                    return match.group(1)
            elif 'reddit.com' in post_url:
                # Extract Reddit post ID
                match = re.search(r'/comments/([a-zA-Z0-9]+)/', post_url)
                if match:
                    return match.group(1)
            
            # Fallback: use URL hash as post ID
            return hashlib.md5(post_url.encode()).hexdigest()[:10]
            
        except Exception as e:
            logger.error(f"Error extracting post ID: {e}")
            return hashlib.md5(post_url.encode()).hexdigest()[:10]
    
    async def _calculate_rewards(self, profile: SocialProfile, post: SocialPost, verification: Dict) -> Dict[str, Any]:
        """Calculate reward amount with bonuses and multipliers"""
        base_reward = self.reward_config['daily_post']['base_amount']
        multiplier = 1.0
        bonuses = []
        
        # Streak bonus
        current_streak = profile.current_streak
        for streak_days, streak_multiplier in self.reward_config['daily_post']['streak_multipliers'].items():
            if current_streak >= streak_days:
                multiplier = streak_multiplier
                bonuses.append(f"{streak_days}-day streak: {streak_multiplier}x multiplier")
        
        # Quality bonus (based on hashtags, content quality)
        if verification.get('has_hashtags'):
            multiplier += 0.1
            bonuses.append("Quality hashtags: +10%")
        
        # Weekend bonus
        if datetime.utcnow().weekday() >= 5:  # Saturday or Sunday
            multiplier += 0.2
            bonuses.append("Weekend posting: +20%")
        
        # Platform diversity bonus
        platforms_used_today = self.db.query(SocialPost).filter(
            SocialPost.wallet_address == profile.wallet_address,
            SocialPost.created_date >= datetime.utcnow().date()
        ).count()
        
        if platforms_used_today > 1:
            multiplier += 0.15 * (platforms_used_today - 1)
            bonuses.append(f"Multi-platform: +{15 * (platforms_used_today - 1)}%")
        
        total_amount = base_reward * multiplier
        
        # Cap the daily amount
        max_daily = self.reward_config['daily_post']['max_daily']
        if total_amount > max_daily:
            total_amount = max_daily
            bonuses.append(f"Capped at daily maximum: {max_daily} $GPUDX")
        
        return {
            'base_amount': base_reward,
            'multiplier': multiplier,
            'total_amount': total_amount,
            'bonuses': bonuses,
            'streak_bonus': current_streak >= 7
        }
    
    async def _check_achievements(self, profile: SocialProfile) -> List[Dict[str, Any]]:
        """Check and unlock new achievements"""
        new_achievements = []
        
        for achievement in self.achievements:
            # Skip if already unlocked
            if achievement.achievement_id in profile.achievements_unlocked:
                continue
            
            # Check unlock conditions
            unlocked = False
            
            if "post_count" in achievement.unlock_condition:
                required_posts = int(achievement.unlock_condition.split(">=")[1].strip())
                if profile.total_posts >= required_posts:
                    unlocked = True
            
            elif "streak" in achievement.unlock_condition:
                required_streak = int(achievement.unlock_condition.split(">=")[1].strip())
                if profile.current_streak >= required_streak:
                    unlocked = True
            
            elif "referrals" in achievement.unlock_condition:
                required_referrals = int(achievement.unlock_condition.split(">=")[1].strip())
                if profile.referrals_count >= required_referrals:
                    unlocked = True
            
            if unlocked:
                # Unlock achievement
                if profile.achievements_unlocked is None:
                    profile.achievements_unlocked = []
                profile.achievements_unlocked.append(achievement.achievement_id)
                profile.achievement_points += int(achievement.reward_amount)
                
                # Award achievement tokens
                await self._award_tokens(
                    profile.wallet_address,
                    achievement.reward_amount,
                    RewardType.ACHIEVEMENT,
                    f"Achievement unlocked: {achievement.name}"
                )
                
                new_achievements.append({
                    'id': achievement.achievement_id,
                    'name': achievement.name,
                    'description': achievement.description,
                    'icon': achievement.icon,
                    'reward': achievement.reward_amount,
                    'rarity': achievement.rarity
                })
        
        return new_achievements
    
    async def _award_tokens(self, wallet_address: str, amount: float, reward_type: RewardType, description: str):
        """Award $GPUDX tokens to user"""
        try:
            reward_record = SocialRewardHistory(
                wallet_address=wallet_address,
                reward_type=reward_type.value,
                amount=amount,
                platform='social_gamification',
                description=description
            )
            self.db.add(reward_record)
            
            # In production, this would trigger actual token transfer
            logger.info(f"Awarded {amount} $GPUDX to {wallet_address} for {description}")
            
        except Exception as e:
            logger.error(f"Error awarding tokens: {e}")
    
    async def get_user_dashboard(self, wallet_address: str) -> Dict[str, Any]:
        """Get comprehensive gamification dashboard for user"""
        try:
            profile = await self._get_or_create_profile(wallet_address)
            
            # Get recent posts
            recent_posts = self.db.query(SocialPost).filter(
                SocialPost.wallet_address == wallet_address
            ).order_by(SocialPost.created_date.desc()).limit(10).all()
            
            # Get reward history
            recent_rewards = self.db.query(SocialRewardHistory).filter(
                SocialRewardHistory.wallet_address == wallet_address
            ).order_by(SocialRewardHistory.created_date.desc()).limit(20).all()
            
            # Calculate today's potential
            todays_potential = await self._calculate_todays_potential(wallet_address)
            
            # Get leaderboard position
            leaderboard_ranks = {
                'daily': await self._get_user_rank(wallet_address, 'daily'),
                'weekly': await self._get_user_rank(wallet_address, 'weekly'),
                'monthly': await self._get_user_rank(wallet_address, 'monthly'),
                'all_time': await self._get_user_rank(wallet_address, 'all_time')
            }
            
            return {
                'profile': {
                    'wallet_address': profile.wallet_address,
                    'total_posts': profile.total_posts,
                    'current_streak': profile.current_streak,
                    'longest_streak': profile.longest_streak,
                    'total_rewards': profile.total_rewards_earned,
                    'user_level': profile.user_level,
                    'achievement_points': profile.achievement_points,
                    'referrals': profile.referrals_count
                },
                'achievements': {
                    'unlocked': len(profile.achievements_unlocked) if profile.achievements_unlocked else 0,
                    'total_available': len(self.achievements),
                    'recent_unlocked': [ach for ach in self.achievements if ach.achievement_id in (profile.achievements_unlocked or [])][-3:],
                    'next_milestone': self._get_next_achievement_milestone(profile)
                },
                'todays_opportunity': todays_potential,
                'recent_activity': [
                    {
                        'type': 'post',
                        'platform': post.platform,
                        'reward': post.reward_amount,
                        'engagement': post.engagement_score,
                        'timestamp': post.created_date.isoformat()
                    } for post in recent_posts
                ],
                'leaderboard': leaderboard_ranks,
                'challenges': self._get_active_challenges(),
                'tomorrow_challenge': self._get_tomorrows_challenge()
            }
            
        except Exception as e:
            logger.error(f"Error getting user dashboard: {e}")
            return {'error': str(e)}
    
    async def get_leaderboard(self, period: str = 'weekly', limit: int = 100) -> Dict[str, Any]:
        """Get social media leaderboard"""
        try:
            # Calculate date range
            now = datetime.utcnow()
            if period == 'daily':
                start_date = now.date()
            elif period == 'weekly':
                start_date = now - timedelta(days=7)
            elif period == 'monthly':
                start_date = now - timedelta(days=30)
            else:  # all_time
                start_date = datetime(2024, 1, 1)
            
            # Get top users by rewards earned
            top_users = self.db.query(
                SocialRewardHistory.wallet_address,
                self.db.func.sum(SocialRewardHistory.amount).label('total_rewards'),
                self.db.func.count(SocialRewardHistory.id).label('activity_count')
            ).filter(
                SocialRewardHistory.created_date >= start_date
            ).group_by(
                SocialRewardHistory.wallet_address
            ).order_by(
                self.db.func.sum(SocialRewardHistory.amount).desc()
            ).limit(limit).all()
            
            leaderboard = []
            for rank, (wallet_address, total_rewards, activity_count) in enumerate(top_users, 1):
                # Get user profile for additional info
                profile = self.db.query(SocialProfile).filter(
                    SocialProfile.wallet_address == wallet_address
                ).first()
                
                leaderboard.append({
                    'rank': rank,
                    'wallet_address': wallet_address,
                    'display_name': f"User {wallet_address[:8]}...",
                    'total_rewards': float(total_rewards),
                    'activity_count': activity_count,
                    'current_streak': profile.current_streak if profile else 0,
                    'achievements_count': len(profile.achievements_unlocked) if profile and profile.achievements_unlocked else 0
                })
            
            return {
                'period': period,
                'leaderboard': leaderboard,
                'total_participants': len(top_users),
                'total_rewards_distributed': sum([user['total_rewards'] for user in leaderboard]),
                'last_updated': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return {'error': str(e)}
    
    # Helper methods
    
    async def _get_or_create_profile(self, wallet_address: str) -> SocialProfile:
        """Get or create social profile"""
        profile = self.db.query(SocialProfile).filter(
            SocialProfile.wallet_address == wallet_address
        ).first()
        
        if not profile:
            profile = SocialProfile(wallet_address=wallet_address)
            self.db.add(profile)
            self.db.commit()
        
        return profile
    
    def _get_posting_requirements(self) -> Dict[str, Any]:
        """Get posting requirements for rewards"""
        return {
            'required_mention': '@GPUDex (honor system - please include this!)',
            'recommended_hashtags': ['#GPUDex', '#GPU', '#DeFi', '#Crypto'],
            'daily_limit': '1 post per platform per day',
            'supported_platforms': ['Twitter/X', 'LinkedIn', 'Reddit', 'Discord'],
            'minimum_content': 'Must be original content mentioning GPUDex',
            'verification': 'Honor system - we trust our community! 🤝',
            'future_upgrades': 'Screenshot verification and community voting coming soon'
        }
    
    def _get_daily_posting_info(self) -> Dict[str, Any]:
        """Get information about daily posting rewards"""
        return {
            'base_reward': f"{self.reward_config['daily_post']['base_amount']} $GPUDX",
            'max_daily': f"{self.reward_config['daily_post']['max_daily']} $GPUDX",
            'streak_bonuses': {
                '7_days': '1.5x multiplier',
                '30_days': '2x multiplier', 
                '100_days': '3x multiplier',
                '365_days': '5x multiplier'
            },
            'bonus_opportunities': [
                'Quality hashtags: +10%',
                'Weekend posting: +20%',
                'Multi-platform: +15% per additional platform'
            ]
        }
    
    def _get_next_streak_milestone(self, current_streak: int) -> Dict[str, Any]:
        """Get next streak milestone"""
        milestones = [7, 30, 100, 365]
        for milestone in milestones:
            if current_streak < milestone:
                return {
                    'days': milestone,
                    'days_remaining': milestone - current_streak,
                    'reward_multiplier': self.reward_config['daily_post']['streak_multipliers'][milestone]
                }
        return {'days': 730, 'days_remaining': 730 - current_streak, 'reward_multiplier': 10.0}
    
    def _get_tomorrows_challenge(self) -> Dict[str, Any]:
        """Get tomorrow's daily challenge"""
        tomorrow = datetime.utcnow() + timedelta(days=1)
        day_name = tomorrow.strftime('%A')
        
        challenge_map = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        
        challenge_index = challenge_map.get(day_name, 0)
        if challenge_index < len(self.daily_challenges):
            return self.daily_challenges[challenge_index]
        
        return self.daily_challenges[0]
    
    def _get_active_challenges(self) -> List[Dict[str, Any]]:
        """Get currently active challenges"""
        now = datetime.utcnow()
        
        active_challenges = self.db.query(DailyChallenge).filter(
            DailyChallenge.is_active == True,
            DailyChallenge.start_date <= now,
            DailyChallenge.end_date >= now
        ).all()
        
        return [
            {
                'id': challenge.challenge_id,
                'title': challenge.title,
                'description': challenge.description,
                'reward': challenge.base_reward,
                'participants': challenge.total_participants,
                'time_remaining': (challenge.end_date - now).total_seconds()
            } for challenge in active_challenges
        ]
    
    async def _calculate_todays_potential(self, wallet_address: str) -> Dict[str, Any]:
        """Calculate today's earning potential"""
        today = datetime.utcnow().date()
        posts_today = self.db.query(SocialPost).filter(
            SocialPost.wallet_address == wallet_address,
            SocialPost.created_date >= today
        ).count()
        
        profile = await self._get_or_create_profile(wallet_address)
        
        # Calculate potential rewards for remaining platforms
        platforms_posted = [SocialPlatform.TWITTER, SocialPlatform.LINKEDIN, SocialPlatform.REDDIT]
        remaining_platforms = len(platforms_posted) - posts_today
        
        base_reward = self.reward_config['daily_post']['base_amount']
        streak_multiplier = 1.0
        
        for streak_days, multiplier in self.reward_config['daily_post']['streak_multipliers'].items():
            if profile.current_streak >= streak_days:
                streak_multiplier = multiplier
        
        potential_per_post = base_reward * streak_multiplier
        total_potential = potential_per_post * remaining_platforms
        
        return {
            'posts_made_today': posts_today,
            'remaining_opportunities': remaining_platforms,
            'potential_per_post': potential_per_post,
            'total_potential_today': total_potential,
            'current_streak': profile.current_streak,
            'streak_multiplier': streak_multiplier
        }
    
    async def _get_user_rank(self, wallet_address: str, period: str) -> int:
        """Get user's rank in leaderboard"""
        # Simplified ranking - in production would be more sophisticated
        return 42  # Placeholder
    
    def _get_next_achievement_milestone(self, profile: SocialProfile) -> Dict[str, Any]:
        """Get next achievement milestone"""
        unlocked_count = len(profile.achievements_unlocked) if profile.achievements_unlocked else 0
        
        # Find next post-count achievement
        for achievement in self.achievements:
            if "post_count" in achievement.unlock_condition:
                required_posts = int(achievement.unlock_condition.split(">=")[1].strip())
                if profile.total_posts < required_posts:
                    return {
                        'achievement': achievement.name,
                        'description': achievement.description,
                        'reward': achievement.reward_amount,
                        'progress': profile.total_posts,
                        'target': required_posts,
                        'remaining': required_posts - profile.total_posts
                    }
        
        return {'achievement': 'All achievements unlocked!', 'progress': 100, 'target': 100}

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import os
    
    # Configuration
    config = {
        'database_url': os.getenv('DATABASE_URL', 'postgresql://gpudex:password@postgres:5432/gpudex_db'),
        'rpc_url': os.getenv('RPC_URL', 'https://polygon-rpc.com'),
        'token_contract_address': os.getenv('GPUDX_TOKEN_V2_ADDRESS', '0x5FbDB2315678afecb367f032d93F642f64180aa3'),
        'port': int(os.getenv('SOCIAL_GAMIFICATION_PORT', '8005'))
    }
    
    # Initialize social gamification service
    social_service = SocialGamificationService()
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx Social Gamification Service", version="2.0.0")

    # ===============================================================================
    # 🎮 SOCIAL GAMIFICATION API ENDPOINTS - EARN TOKENS THROUGH SOCIAL MEDIA! 🎮
    # ===============================================================================

    @app.post("/api/v1/social/register")
    async def register_social_profile_endpoint(data: dict):
        """Register social media accounts for gamification"""
        try:
            wallet_address = data.get('wallet_address')
            social_data = data.get('social_data', {})
            
            result = await social_service.register_social_profile(wallet_address, social_data)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Failed to register social profile: {e}")
            return {"success": False, "error": str(e)}

    @app.post("/api/v1/social/submit-post")
    async def submit_daily_post_endpoint(data: dict):
        """Submit daily social media post for token rewards"""
        try:
            wallet_address = data.get('wallet_address')
            post_url = data.get('post_url')
            platform = data.get('platform')
            
            result = await social_service.submit_daily_post(wallet_address, post_url, platform)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Failed to submit post: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/v1/social/dashboard/{wallet_address}")
    async def get_user_dashboard_endpoint(wallet_address: str):
        """Get user's social gamification dashboard"""
        try:
            result = await social_service.get_user_dashboard(wallet_address)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Failed to get dashboard: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/v1/social/leaderboard")
    async def get_leaderboard_endpoint(period: str = 'weekly', limit: int = 50):
        """Get social gamification leaderboard"""
        try:
            result = await social_service.get_leaderboard(period, limit)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/v1/social/achievements")
    async def get_achievements_endpoint():
        """Get all available achievements"""
        try:
            achievements_data = []
            for achievement in social_service.achievements:
                achievements_data.append({
                    'id': achievement.achievement_id,
                    'name': achievement.name,
                    'description': achievement.description,
                    'icon': achievement.icon,
                    'reward_amount': achievement.reward_amount,
                    'rarity': achievement.rarity,
                    'unlock_condition': achievement.unlock_condition
                })
            return {"success": True, "data": {"achievements": achievements_data}}
        except Exception as e:
            logger.error(f"Failed to get achievements: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/v1/social/challenges")
    async def get_daily_challenges_endpoint():
        """Get current daily challenges"""
        try:
            return {"success": True, "data": {"challenges": social_service.daily_challenges}}
        except Exception as e:
            logger.error(f"Failed to get challenges: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/v1/social/rewards/{wallet_address}")
    async def get_reward_history_endpoint(wallet_address: str, limit: int = 50):
        """Get user's reward history"""
        try:
            # This would query the SocialRewardHistory table
            # For now, return mock data structure
            result = {
                'total_earned': 0,
                'this_week': 0,
                'pending_rewards': 0,
                'reward_history': []
            }
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Failed to get reward history: {e}")
            return {"success": False, "error": str(e)}

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:80", "http://127.0.0.1", "http://127.0.0.1:80"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {"message": "GPUDx Social Gamification Service", "status": "operational"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "social_gamification"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from fastapi import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return {"error": "Prometheus client not available", "service": "social_gamification"}
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=config['port']) 
