#!/usr/bin/env python3
"""
GPUDex Community Onboarding Service
Manages utility-earning programs, social gamification, and user onboarding
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import sqlite3
import aiohttp
from enum import Enum
import hashlib
import secrets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserTier(Enum):
    NONE = 0
    BRONZE = 1
    SILVER = 2
    GOLD = 3
    DIAMOND = 4

class ActivityType(Enum):
    FIRST_RENTAL = "first_rental"
    POWER_USER = "power_user"
    LOYAL_CUSTOMER = "loyal_customer"
    PROVIDER_DEBUT = "provider_debut"
    HIGH_RATING = "high_rating"
    REFERRAL_SIGNUP = "referral_signup"
    SOCIAL_SHARE = "social_share"
    TUTORIAL_COMPLETE = "tutorial_complete"
    FEEDBACK_SUBMIT = "feedback_submit"
    COMMUNITY_HELP = "community_help"

@dataclass
class Achievement:
    """User achievement data structure"""
    id: str
    name: str
    description: str
    reward_amount: float
    tier_requirement: UserTier
    progress_current: int
    progress_required: int
    unlocked: bool
    unlocked_at: Optional[float]
    category: str

@dataclass
class UserProfile:
    """Comprehensive user profile for onboarding"""
    address: str
    joined_at: float
    tier: UserTier
    staked_amount: float
    total_gpu_spending: float
    total_gpu_hours: int
    referral_count: int
    social_points: int
    achievements_unlocked: int
    onboarding_completed: bool
    last_activity: float
    favorite_gpu_tier: str
    total_savings: float

@dataclass
class OnboardingTask:
    """Individual onboarding task"""
    task_id: str
    title: str
    description: str
    reward_amount: float
    completed: bool
    completion_time: Optional[float]
    tutorial_link: Optional[str]
    verification_required: bool

class CommunityOnboardingService:
    """Service for managing community onboarding and gamification"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_path = config.get('database_path', 'community_onboarding.db')
        
        # Initialize database
        self._init_database()
        
        # Load reward configurations
        self._load_reward_configs()
        
        # Initialize achievement system
        self._init_achievements()
    
    def _init_database(self):
        """Initialize SQLite database for community data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                address TEXT PRIMARY KEY,
                joined_at REAL NOT NULL,
                tier INTEGER DEFAULT 0,
                staked_amount REAL DEFAULT 0,
                total_gpu_spending REAL DEFAULT 0,
                total_gpu_hours INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                social_points INTEGER DEFAULT 0,
                achievements_unlocked INTEGER DEFAULT 0,
                onboarding_completed BOOLEAN DEFAULT FALSE,
                last_activity REAL,
                favorite_gpu_tier TEXT DEFAULT 'BASIC',
                total_savings REAL DEFAULT 0,
                referrer_address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                reward_amount REAL NOT NULL,
                tier_requirement INTEGER DEFAULT 0,
                progress_required INTEGER DEFAULT 1,
                category TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_address TEXT NOT NULL,
                achievement_id TEXT NOT NULL,
                progress_current INTEGER DEFAULT 0,
                unlocked BOOLEAN DEFAULT FALSE,
                unlocked_at REAL,
                reward_claimed BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_address) REFERENCES user_profiles(address),
                FOREIGN KEY (achievement_id) REFERENCES achievements(id)
            )
        ''')
        
        # Onboarding tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS onboarding_tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                reward_amount REAL NOT NULL,
                tutorial_link TEXT,
                verification_required BOOLEAN DEFAULT FALSE,
                order_index INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User onboarding progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_onboarding_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_address TEXT NOT NULL,
                task_id TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                completion_time REAL,
                reward_claimed BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_address) REFERENCES user_profiles(address),
                FOREIGN KEY (task_id) REFERENCES onboarding_tasks(task_id)
            )
        ''')
        
        # Referral tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_address TEXT NOT NULL,
                referee_address TEXT NOT NULL,
                referral_code TEXT,
                signup_time REAL NOT NULL,
                reward_amount REAL DEFAULT 0,
                reward_claimed BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_address) REFERENCES user_profiles(address),
                FOREIGN KEY (referee_address) REFERENCES user_profiles(address)
            )
        ''')
        
        # Social activity tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_address TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                platform TEXT,
                content_url TEXT,
                engagement_score INTEGER DEFAULT 0,
                reward_amount REAL DEFAULT 0,
                verified BOOLEAN DEFAULT FALSE,
                timestamp REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_address) REFERENCES user_profiles(address)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Community onboarding database initialized successfully")
    
    def _load_reward_configs(self):
        """Load reward configuration for different activities"""
        self.reward_configs = {
            ActivityType.FIRST_RENTAL: {
                "amount": 50.0,
                "description": "Complete your first GPU rental",
                "tier_requirement": UserTier.NONE
            },
            ActivityType.POWER_USER: {
                "amount": 200.0,
                "description": "Rent GPUs for 100+ hours total",
                "tier_requirement": UserTier.BRONZE
            },
            ActivityType.LOYAL_CUSTOMER: {
                "amount": 100.0,
                "description": "Complete 10+ GPU rentals",
                "tier_requirement": UserTier.BRONZE
            },
            ActivityType.PROVIDER_DEBUT: {
                "amount": 75.0,
                "description": "List your first GPU for rental",
                "tier_requirement": UserTier.BRONZE
            },
            ActivityType.HIGH_RATING: {
                "amount": 25.0,
                "description": "Maintain 95%+ rating with 5+ rentals",
                "tier_requirement": UserTier.SILVER
            },
            ActivityType.REFERRAL_SIGNUP: {
                "amount": 50.0,
                "description": "Successfully refer a new user",
                "tier_requirement": UserTier.NONE
            },
            ActivityType.SOCIAL_SHARE: {
                "amount": 10.0,
                "description": "Share GPUDex on social media",
                "tier_requirement": UserTier.NONE
            },
            ActivityType.TUTORIAL_COMPLETE: {
                "amount": 25.0,
                "description": "Complete platform tutorial",
                "tier_requirement": UserTier.NONE
            },
            ActivityType.FEEDBACK_SUBMIT: {
                "amount": 15.0,
                "description": "Submit valuable platform feedback",
                "tier_requirement": UserTier.NONE
            },
            ActivityType.COMMUNITY_HELP: {
                "amount": 20.0,
                "description": "Help other users in community",
                "tier_requirement": UserTier.BRONZE
            }
        }
    
    def _init_achievements(self):
        """Initialize achievement system with default achievements"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Default achievements
        default_achievements = [
            {
                "id": "first_steps",
                "name": "First Steps",
                "description": "Complete your first GPU rental",
                "reward_amount": 50.0,
                "tier_requirement": 0,
                "progress_required": 1,
                "category": "getting_started"
            },
            {
                "id": "gpu_enthusiast",
                "name": "GPU Enthusiast",
                "description": "Rent GPUs for 50+ hours",
                "reward_amount": 100.0,
                "tier_requirement": 1,
                "progress_required": 50,
                "category": "usage"
            },
            {
                "id": "power_user",
                "name": "Power User",
                "description": "Rent GPUs for 100+ hours",
                "reward_amount": 200.0,
                "tier_requirement": 1,
                "progress_required": 100,
                "category": "usage"
            },
            {
                "id": "gpu_master",
                "name": "GPU Master",
                "description": "Rent GPUs for 500+ hours",
                "reward_amount": 500.0,
                "tier_requirement": 2,
                "progress_required": 500,
                "category": "usage"
            },
            {
                "id": "provider_pioneer",
                "name": "Provider Pioneer",
                "description": "Successfully provide GPU rentals to 10+ users",
                "reward_amount": 150.0,
                "tier_requirement": 1,
                "progress_required": 10,
                "category": "providing"
            },
            {
                "id": "community_champion",
                "name": "Community Champion",
                "description": "Refer 5+ successful users",
                "reward_amount": 250.0,
                "tier_requirement": 1,
                "progress_required": 5,
                "category": "community"
            },
            {
                "id": "social_influencer",
                "name": "Social Influencer",
                "description": "Share GPUDex content 20+ times",
                "reward_amount": 200.0,
                "tier_requirement": 0,
                "progress_required": 20,
                "category": "social"
            },
            {
                "id": "diamond_elite",
                "name": "Diamond Elite",
                "description": "Reach Diamond staking tier",
                "reward_amount": 1000.0,
                "tier_requirement": 4,
                "progress_required": 1,
                "category": "staking"
            }
        ]
        
        for achievement in default_achievements:
            cursor.execute('''
                INSERT OR IGNORE INTO achievements 
                (id, name, description, reward_amount, tier_requirement, progress_required, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                achievement["id"],
                achievement["name"],
                achievement["description"],
                achievement["reward_amount"],
                achievement["tier_requirement"],
                achievement["progress_required"],
                achievement["category"]
            ))
        
        # Default onboarding tasks
        default_tasks = [
            {
                "task_id": "welcome_tutorial",
                "title": "Complete Welcome Tutorial",
                "description": "Learn the basics of GPUDex platform",
                "reward_amount": 25.0,
                "tutorial_link": "https://docs.gpudex.com/getting-started",
                "verification_required": False,
                "order_index": 1
            },
            {
                "task_id": "setup_wallet",
                "title": "Connect Your Wallet",
                "description": "Connect a Web3 wallet to access the platform",
                "reward_amount": 20.0,
                "tutorial_link": "https://docs.gpudex.com/wallet-setup",
                "verification_required": True,
                "order_index": 2
            },
            {
                "task_id": "stake_tokens",
                "title": "Stake Your First GPUDX Tokens",
                "description": "Stake at least 1000 GPUDX to unlock benefits",
                "reward_amount": 50.0,
                "tutorial_link": "https://docs.gpudex.com/staking-guide",
                "verification_required": True,
                "order_index": 3
            },
            {
                "task_id": "first_rental",
                "title": "Rent Your First GPU",
                "description": "Complete your first GPU rental transaction",
                "reward_amount": 75.0,
                "tutorial_link": "https://docs.gpudex.com/renting-gpus",
                "verification_required": True,
                "order_index": 4
            },
            {
                "task_id": "join_community",
                "title": "Join the Community",
                "description": "Join our Discord and introduce yourself",
                "reward_amount": 30.0,
                "tutorial_link": "https://discord.gg/gpudx",
                "verification_required": False,
                "order_index": 5
            },
            {
                "task_id": "social_share",
                "title": "Share on Social Media",
                "description": "Share your GPUDex experience on social media",
                "reward_amount": 25.0,
                "tutorial_link": "https://docs.gpudex.com/social-sharing",
                "verification_required": False,
                "order_index": 6
            },
            {
                "task_id": "provide_feedback",
                "title": "Provide Platform Feedback",
                "description": "Help us improve by sharing your feedback",
                "reward_amount": 40.0,
                "tutorial_link": "https://feedback.gpudex.com",
                "verification_required": False,
                "order_index": 7
            }
        ]
        
        for task in default_tasks:
            cursor.execute('''
                INSERT OR IGNORE INTO onboarding_tasks 
                (task_id, title, description, reward_amount, tutorial_link, verification_required, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task["task_id"],
                task["title"],
                task["description"],
                task["reward_amount"],
                task["tutorial_link"],
                task["verification_required"],
                task["order_index"]
            ))
        
        conn.commit()
        conn.close()
        logger.info("Default achievements and onboarding tasks initialized")
    
    async def register_user(self, user_address: str, referrer_address: Optional[str] = None) -> UserProfile:
        """Register a new user and initialize their onboarding journey"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute('SELECT address FROM user_profiles WHERE address = ?', (user_address,))
            if cursor.fetchone():
                conn.close()
                return await self.get_user_profile(user_address)
            
            # Create new user profile
            join_time = time.time()
            cursor.execute('''
                INSERT INTO user_profiles 
                (address, joined_at, last_activity, referrer_address)
                VALUES (?, ?, ?, ?)
            ''', (user_address, join_time, join_time, referrer_address))
            
            # Initialize user achievements
            cursor.execute('SELECT id FROM achievements')
            achievements = cursor.fetchall()
            
            for (achievement_id,) in achievements:
                cursor.execute('''
                    INSERT INTO user_achievements 
                    (user_address, achievement_id, progress_current)
                    VALUES (?, ?, 0)
                ''', (user_address, achievement_id))
            
            # Initialize onboarding tasks
            cursor.execute('SELECT task_id FROM onboarding_tasks ORDER BY order_index')
            tasks = cursor.fetchall()
            
            for (task_id,) in tasks:
                cursor.execute('''
                    INSERT INTO user_onboarding_progress 
                    (user_address, task_id)
                    VALUES (?, ?)
                ''', (user_address, task_id))
            
            # Process referral if provided
            if referrer_address:
                referral_code = self._generate_referral_code(referrer_address, user_address)
                cursor.execute('''
                    INSERT INTO referrals 
                    (referrer_address, referee_address, referral_code, signup_time, reward_amount)
                    VALUES (?, ?, ?, ?, ?)
                ''', (referrer_address, user_address, referral_code, join_time, 50.0))
                
                # Update referrer's referral count
                cursor.execute('''
                    UPDATE user_profiles 
                    SET referral_count = referral_count + 1 
                    WHERE address = ?
                ''', (referrer_address,))
                
                # Award referral achievement progress
                await self._update_achievement_progress(referrer_address, "community_champion", 1)
            
            conn.commit()
            conn.close()
            
            logger.info(f"New user registered: {user_address}")
            
            # Award welcome bonus
            await self._award_welcome_bonus(user_address)
            
            return await self.get_user_profile(user_address)
            
        except Exception as e:
            logger.error(f"Error registering user {user_address}: {e}")
            raise
    
    def _generate_referral_code(self, referrer: str, referee: str) -> str:
        """Generate a unique referral code"""
        data = f"{referrer}:{referee}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]
    
    async def _award_welcome_bonus(self, user_address: str):
        """Award welcome bonus to new users"""
        try:
            # Award 25 GPUDX welcome bonus
            await self.track_social_activity(
                user_address=user_address,
                activity_type="welcome_bonus",
                platform="gpudex",
                reward_amount=25.0
            )
            logger.info(f"Welcome bonus awarded to {user_address}")
            
        except Exception as e:
            logger.error(f"Error awarding welcome bonus to {user_address}: {e}")
    
    async def get_user_profile(self, user_address: str) -> Optional[UserProfile]:
        """Get comprehensive user profile"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_profiles WHERE address = ?
            ''', (user_address,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            columns = [desc[0] for desc in cursor.description]
            profile_data = dict(zip(columns, row))
            
            # Get achievements count
            cursor.execute('''
                SELECT COUNT(*) FROM user_achievements 
                WHERE user_address = ? AND unlocked = TRUE
            ''', (user_address,))
            achievements_unlocked = cursor.fetchone()[0]
            
            conn.close()
            
            return UserProfile(
                address=profile_data['address'],
                joined_at=profile_data['joined_at'],
                tier=UserTier(profile_data['tier']),
                staked_amount=profile_data['staked_amount'],
                total_gpu_spending=profile_data['total_gpu_spending'],
                total_gpu_hours=profile_data['total_gpu_hours'],
                referral_count=profile_data['referral_count'],
                social_points=profile_data['social_points'],
                achievements_unlocked=achievements_unlocked,
                onboarding_completed=profile_data['onboarding_completed'],
                last_activity=profile_data['last_activity'],
                favorite_gpu_tier=profile_data['favorite_gpu_tier'],
                total_savings=profile_data['total_savings']
            )
            
        except Exception as e:
            logger.error(f"Error getting user profile {user_address}: {e}")
            return None
    
    async def complete_onboarding_task(self, user_address: str, task_id: str, verification_data: Optional[Dict] = None) -> bool:
        """Complete an onboarding task and award rewards"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if task exists and is not completed
            cursor.execute('''
                SELECT uop.completed, ot.reward_amount, ot.verification_required 
                FROM user_onboarding_progress uop
                JOIN onboarding_tasks ot ON uop.task_id = ot.task_id
                WHERE uop.user_address = ? AND uop.task_id = ?
            ''', (user_address, task_id))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            
            completed, reward_amount, verification_required = result
            
            if completed:
                conn.close()
                return True  # Already completed
            
            # Verify task completion if required
            if verification_required and not await self._verify_task_completion(user_address, task_id, verification_data):
                conn.close()
                return False
            
            # Mark task as completed
            completion_time = time.time()
            cursor.execute('''
                UPDATE user_onboarding_progress 
                SET completed = TRUE, completion_time = ?
                WHERE user_address = ? AND task_id = ?
            ''', (completion_time, user_address, task_id))
            
            # Award reward
            cursor.execute('''
                UPDATE user_profiles 
                SET social_points = social_points + ?, last_activity = ?
                WHERE address = ?
            ''', (reward_amount, completion_time, user_address))
            
            # Check if all onboarding tasks are completed
            cursor.execute('''
                SELECT COUNT(*) as total, SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed
                FROM user_onboarding_progress 
                WHERE user_address = ?
            ''', (user_address,))
            
            total, completed_count = cursor.fetchone()
            
            if total == completed_count:
                # Mark onboarding as completed and award bonus
                cursor.execute('''
                    UPDATE user_profiles 
                    SET onboarding_completed = TRUE, social_points = social_points + 100
                    WHERE address = ?
                ''', (user_address,))
                
                logger.info(f"User {user_address} completed onboarding! Bonus awarded.")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Task {task_id} completed by {user_address}, reward: {reward_amount} GPUDX")
            return True
            
        except Exception as e:
            logger.error(f"Error completing onboarding task {task_id} for {user_address}: {e}")
            return False
    
    async def _verify_task_completion(self, user_address: str, task_id: str, verification_data: Optional[Dict]) -> bool:
        """Verify task completion based on task type"""
        try:
            if task_id == "setup_wallet":
                # Verify wallet connection (would integrate with frontend)
                return verification_data and verification_data.get("wallet_connected", False)
            
            elif task_id == "stake_tokens":
                # Verify staking amount (would check smart contract)
                return verification_data and verification_data.get("staked_amount", 0) >= 1000
            
            elif task_id == "first_rental":
                # Verify first rental completion (would check rental records)
                return verification_data and verification_data.get("rental_completed", False)
            
            else:
                # Tasks that don't require verification
                return True
                
        except Exception as e:
            logger.error(f"Error verifying task {task_id} for {user_address}: {e}")
            return False
    
    async def track_social_activity(self, user_address: str, activity_type: str, platform: str, 
                                  content_url: Optional[str] = None, reward_amount: float = 0) -> bool:
        """Track social media activity and award rewards"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = time.time()
            
            cursor.execute('''
                INSERT INTO social_activities 
                (user_address, activity_type, platform, content_url, reward_amount, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_address, activity_type, platform, content_url, reward_amount, timestamp))
            
            # Award social points
            if reward_amount > 0:
                cursor.execute('''
                    UPDATE user_profiles 
                    SET social_points = social_points + ?, last_activity = ?
                    WHERE address = ?
                ''', (reward_amount, timestamp, user_address))
                
                # Update social achievement progress
                await self._update_achievement_progress(user_address, "social_influencer", 1)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Social activity tracked: {activity_type} by {user_address}, reward: {reward_amount}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking social activity for {user_address}: {e}")
            return False
    
    async def _update_achievement_progress(self, user_address: str, achievement_id: str, progress_increment: int):
        """Update user's progress toward an achievement"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current progress and requirements
            cursor.execute('''
                SELECT ua.progress_current, ua.unlocked, a.progress_required, a.reward_amount
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.id
                WHERE ua.user_address = ? AND ua.achievement_id = ?
            ''', (user_address, achievement_id))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return
            
            current_progress, unlocked, required_progress, reward_amount = result
            
            if unlocked:
                conn.close()
                return  # Already unlocked
            
            # Update progress
            new_progress = current_progress + progress_increment
            
            if new_progress >= required_progress:
                # Achievement unlocked!
                unlock_time = time.time()
                cursor.execute('''
                    UPDATE user_achievements 
                    SET progress_current = ?, unlocked = TRUE, unlocked_at = ?
                    WHERE user_address = ? AND achievement_id = ?
                ''', (new_progress, unlock_time, user_address, achievement_id))
                
                # Award achievement reward
                cursor.execute('''
                    UPDATE user_profiles 
                    SET social_points = social_points + ?, last_activity = ?
                    WHERE address = ?
                ''', (reward_amount, unlock_time, user_address))
                
                logger.info(f"Achievement {achievement_id} unlocked by {user_address}! Reward: {reward_amount}")
                
            else:
                # Update progress only
                cursor.execute('''
                    UPDATE user_achievements 
                    SET progress_current = ?
                    WHERE user_address = ? AND achievement_id = ?
                ''', (new_progress, user_address, achievement_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating achievement progress for {user_address}: {e}")
    
    async def get_user_achievements(self, user_address: str) -> List[Achievement]:
        """Get all achievements for a user with progress"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT a.id, a.name, a.description, a.reward_amount, a.tier_requirement, 
                       a.progress_required, a.category, ua.progress_current, ua.unlocked, ua.unlocked_at
                FROM achievements a
                JOIN user_achievements ua ON a.id = ua.achievement_id
                WHERE ua.user_address = ?
                ORDER BY ua.unlocked DESC, a.reward_amount DESC
            ''', (user_address,))
            
            achievements = []
            for row in cursor.fetchall():
                achievement = Achievement(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    reward_amount=row[3],
                    tier_requirement=UserTier(row[4]),
                    progress_required=row[5],
                    category=row[6],
                    progress_current=row[7],
                    unlocked=bool(row[8]),
                    unlocked_at=row[9]
                )
                achievements.append(achievement)
            
            conn.close()
            return achievements
            
        except Exception as e:
            logger.error(f"Error getting achievements for {user_address}: {e}")
            return []
    
    async def get_onboarding_progress(self, user_address: str) -> List[OnboardingTask]:
        """Get user's onboarding progress"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ot.task_id, ot.title, ot.description, ot.reward_amount, ot.tutorial_link,
                       ot.verification_required, uop.completed, uop.completion_time
                FROM onboarding_tasks ot
                JOIN user_onboarding_progress uop ON ot.task_id = uop.task_id
                WHERE uop.user_address = ?
                ORDER BY ot.order_index
            ''', (user_address,))
            
            tasks = []
            for row in cursor.fetchall():
                task = OnboardingTask(
                    task_id=row[0],
                    title=row[1],
                    description=row[2],
                    reward_amount=row[3],
                    tutorial_link=row[4],
                    verification_required=bool(row[5]),
                    completed=bool(row[6]),
                    completion_time=row[7]
                )
                tasks.append(task)
            
            conn.close()
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting onboarding progress for {user_address}: {e}")
            return []
    
    async def get_leaderboard(self, category: str = "social_points", limit: int = 100) -> List[Dict]:
        """Get community leaderboard"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            valid_categories = ["social_points", "total_gpu_spending", "total_gpu_hours", "referral_count", "achievements_unlocked"]
            if category not in valid_categories:
                category = "social_points"
            
            cursor.execute(f'''
                SELECT address, {category}, tier, achievements_unlocked, joined_at
                FROM user_profiles 
                WHERE {category} > 0
                ORDER BY {category} DESC 
                LIMIT ?
            ''', (limit,))
            
            leaderboard = []
            for i, row in enumerate(cursor.fetchall()):
                entry = {
                    "rank": i + 1,
                    "address": row[0],
                    "value": row[1],
                    "tier": UserTier(row[2]).name,
                    "achievements": row[3],
                    "joined_at": row[4]
                }
                leaderboard.append(entry)
            
            conn.close()
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def get_community_stats(self) -> Dict:
        """Get overall community statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total users
            cursor.execute('SELECT COUNT(*) FROM user_profiles')
            total_users = cursor.fetchone()[0]
            
            # Users by tier
            cursor.execute('SELECT tier, COUNT(*) FROM user_profiles GROUP BY tier')
            tier_distribution = {UserTier(tier).name: count for tier, count in cursor.fetchall()}
            
            # Total rewards distributed
            cursor.execute('SELECT SUM(social_points) FROM user_profiles')
            total_rewards = cursor.fetchone()[0] or 0
            
            # Total achievements unlocked
            cursor.execute('SELECT COUNT(*) FROM user_achievements WHERE unlocked = TRUE')
            total_achievements = cursor.fetchone()[0]
            
            # Active users (last 30 days)
            thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
            cursor.execute('SELECT COUNT(*) FROM user_profiles WHERE last_activity > ?', (thirty_days_ago,))
            active_users = cursor.fetchone()[0]
            
            # Total referrals
            cursor.execute('SELECT COUNT(*) FROM referrals')
            total_referrals = cursor.fetchone()[0]
            
            # Onboarding completion rate
            cursor.execute('SELECT COUNT(*) FROM user_profiles WHERE onboarding_completed = TRUE')
            completed_onboarding = cursor.fetchone()[0]
            completion_rate = (completed_onboarding / total_users * 100) if total_users > 0 else 0
            
            conn.close()
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "tier_distribution": tier_distribution,
                "total_rewards_distributed": total_rewards,
                "total_achievements_unlocked": total_achievements,
                "total_referrals": total_referrals,
                "onboarding_completion_rate": completion_rate,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting community stats: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    config = {
        'database_path': 'community_onboarding.db'
    }
    
    service = CommunityOnboardingService(config)
    
    async def test_onboarding():
        # Register a new user
        user_address = "0x1234567890123456789012345678901234567890"
        profile = await service.register_user(user_address)
        print(f"Registered user: {profile.address}")
        
        # Complete onboarding tasks
        await service.complete_onboarding_task(user_address, "welcome_tutorial")
        await service.complete_onboarding_task(user_address, "join_community")
        
        # Track social activity
        await service.track_social_activity(
            user_address, "social_share", "twitter", 
            "https://twitter.com/user/status/123", 10.0
        )
        
        # Get achievements
        achievements = await service.get_user_achievements(user_address)
        print(f"User has {len(achievements)} achievements")
        
        # Get community stats
        stats = await service.get_community_stats()
        print("Community stats:", stats)

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    import os
    
    # Configuration
    config = {
        'database_url': os.getenv('DATABASE_URL', 'postgresql://gpudex:password@postgres:5432/gpudex_db'),
        'rpc_url': os.getenv('RPC_URL', 'https://polygon-rpc.com'),
        'token_contract_address': os.getenv('GPUDX_TOKEN_V2_ADDRESS', '0x5FbDB2315678afecb367f032d93F642f64180aa3'),
        'port': int(os.getenv('COMMUNITY_ONBOARDING_PORT', '8007'))
    }
    
    # Initialize community onboarding service
    community_service = CommunityOnboardingService(config)
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx Community Onboarding Service", version="2.0.0")
    
    @app.get("/")
    async def root():
        return {"message": "GPUDx Community Onboarding Service", "status": "operational"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "community_onboarding"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from fastapi import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return {"error": "Prometheus client not available", "service": "community_onboarding"}
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=config['port']) 