#!/usr/bin/env python3
"""
🔥 VIRAL MARKETING ENGINE - BILL GATES ON ADDERALL EDITION! 🔥
Automated social media growth machine with maximum viral potential!
"""

import asyncio
import json
import logging
import time
import os
import hashlib
import requests
import tweepy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import sqlite3
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ViralPost:
    """Viral social media post data structure"""
    id: str
    user_address: str
    platform: str
    content: str
    image_url: Optional[str]
    achievement_id: Optional[str]
    tier_reached: Optional[str]
    engagement_score: int
    viral_potential: float
    reward_amount: float
    posted_at: float
    verified: bool

@dataclass
class InfluencerStats:
    """Influencer tracking and analytics"""
    address: str
    twitter_handle: Optional[str]
    discord_id: Optional[str]
    follower_count: int
    engagement_rate: float
    total_referrals: int
    total_earnings: float
    tier: str
    verified: bool
    custom_referral_code: str

@dataclass
class ViralCampaign:
    """Viral marketing campaign data"""
    id: str
    name: str
    start_date: float
    end_date: float
    target_platform: str
    reward_per_share: float
    bonus_multiplier: float
    hashtags: List[str]
    target_engagement: int
    current_participants: int
    total_rewards_distributed: float
    active: bool

class ViralMarketingEngine:
    """🚀 EXPLOSIVE VIRAL MARKETING AUTOMATION SYSTEM! 🚀"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_path = config.get('database_path', 'viral_marketing.db')
        
        # Social media API clients
        self.twitter_client = None
        self.discord_client = None
        
        # Initialize components
        self._init_database()
        self._init_social_apis()
        self._load_viral_templates()
        
        logger.info("🔥 Viral Marketing Engine initialized with MAXIMUM VELOCITY!")
    
    def _init_database(self):
        """Initialize viral marketing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Viral posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS viral_posts (
                id TEXT PRIMARY KEY,
                user_address TEXT NOT NULL,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                image_url TEXT,
                achievement_id TEXT,
                tier_reached TEXT,
                engagement_score INTEGER DEFAULT 0,
                viral_potential REAL DEFAULT 0,
                reward_amount REAL DEFAULT 0,
                posted_at REAL NOT NULL,
                verified BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Influencer tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS influencers (
                address TEXT PRIMARY KEY,
                twitter_handle TEXT,
                discord_id TEXT,
                follower_count INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                total_earnings REAL DEFAULT 0,
                tier TEXT DEFAULT 'bronze',
                verified BOOLEAN DEFAULT FALSE,
                custom_referral_code TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Viral campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS viral_campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                start_date REAL NOT NULL,
                end_date REAL NOT NULL,
                target_platform TEXT NOT NULL,
                reward_per_share REAL DEFAULT 10,
                bonus_multiplier REAL DEFAULT 1.5,
                hashtags TEXT NOT NULL,
                target_engagement INTEGER DEFAULT 1000,
                current_participants INTEGER DEFAULT 0,
                total_rewards_distributed REAL DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Social engagement tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_engagement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                engagement_type TEXT NOT NULL, -- like, retweet, comment, share
                user_id TEXT,
                timestamp REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES viral_posts(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Viral marketing database initialized")
    
    def _init_social_apis(self):
        """Initialize social media API clients"""
        try:
            # Twitter API v2 initialization
            if all(key in self.config for key in ['twitter_bearer_token', 'twitter_api_key', 'twitter_api_secret', 'twitter_access_token', 'twitter_access_secret']):
                auth = tweepy.OAuth1UserHandler(
                    self.config['twitter_api_key'],
                    self.config['twitter_api_secret'],
                    self.config['twitter_access_token'],
                    self.config['twitter_access_secret']
                )
                self.twitter_client = tweepy.API(auth)
                logger.info("🐦 Twitter API initialized")
            
            # Discord webhook initialization
            if 'discord_webhook_url' in self.config:
                self.discord_webhook = self.config['discord_webhook_url']
                logger.info("💬 Discord webhook initialized")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize social APIs: {e}")
    
    def _load_viral_templates(self):
        """Load viral content templates for different achievements"""
        self.viral_templates = {
            'tier_upgrade': [
                "🚀 Just reached {tier} tier on @GPUDex! {apy}% APY + {discount}% GPU discounts! Staking {amount} $GPUDX for maximum utility! #GPUDX #Staking #GPU",
                "💎 {tier} tier unlocked! Now earning {apy}% APY on my {amount} $GPUDX stake! No governance complexity, just pure value! #GPUDX #DeFi #GPU",
                "⚡ Level up! {tier} tier means {discount}% off all GPU rentals + {boost}% provider boost! Building the future! #GPUDX #GPU #AI"
            ],
            'achievement_unlock': [
                "🏆 Achievement unlocked: \"{achievement}\"! Earned {reward} $GPUDX on @GPUDex! {description} #GPUDX #Achievement #GPU",
                "🎉 Just unlocked \"{achievement}\" and earned {reward} $GPUDX! Love this utility-first tokenomics! #GPUDX #Rewards #GPU",
                "💥 {achievement} achievement complete! +{reward} $GPUDX to my stack! Who else is building on @GPUDex? #GPUDX #Community"
            ],
            'first_rental': [
                "🖥️ Just completed my first GPU rental on @GPUDex! The future of compute is here! Got {discount}% off with my $GPUDX stake! #GPU #AI #GPUDX",
                "⚡ Rented my first GPU on @GPUDex - seamless experience and real utility from $GPUDX staking! Who needs governance when you have this? #GPUDX",
                "🚀 First @GPUDex rental complete! {hours} hours of {gpu_type} for my AI project. Staking $GPUDX actually saves money! #GPU #DeFi"
            ],
            'provider_earnings': [
                "💰 Just earned {amount} from providing GPU compute on @GPUDex! My {gpu_type} is paying for itself! +{boost}% from $GPUDX staking! #GPU #Passive",
                "🏦 Provider life: {amount} earned this week on @GPUDex! GPU {gpu_type} + $GPUDX staking = automatic income! #GPU #Earnings #GPUDX",
                "💎 Making bank with my spare GPU on @GPUDex! {amount} earned + {boost}% staking boost! This is the future! #GPU #Income"
            ],
            'referral_success': [
                "🤝 Just referred another builder to @GPUDex! Earned {reward} $GPUDX + 5% lifetime earnings! Who wants my referral link? #GPUDX #Referral",
                "👥 Another successful @GPUDex referral! Both of us got {reward} $GPUDX! Building the community one referral at a time! #GPUDX #Community",
                "🌟 Referral rewards hitting different on @GPUDex! {reward} $GPUDX + ongoing passive income! DM for referral! #GPUDX #Passive"
            ]
        }
    
    async def process_achievement_unlock(self, user_address: str, achievement_data: Dict) -> bool:
        """Process achievement unlock and trigger viral content creation"""
        try:
            achievement_id = achievement_data['id']
            achievement_name = achievement_data['name']
            description = achievement_data['description']
            reward = achievement_data['reward']
            
            # Generate viral content
            template_key = self._get_template_key(achievement_id)
            content = self._generate_viral_content(template_key, {
                'achievement': achievement_name,
                'reward': reward,
                'description': description,
                'user': user_address[:6] + '...' + user_address[-4:]
            })
            
            # Create achievement image
            image_path = await self._create_achievement_image(achievement_data)
            
            # Create viral post record
            post_id = self._generate_post_id(user_address, achievement_id)
            viral_post = ViralPost(
                id=post_id,
                user_address=user_address,
                platform='twitter',
                content=content,
                image_url=image_path,
                achievement_id=achievement_id,
                tier_reached=None,
                engagement_score=0,
                viral_potential=self._calculate_viral_potential(achievement_data),
                reward_amount=10.0,  # Base viral sharing reward
                posted_at=time.time(),
                verified=False
            )
            
            # Store in database
            await self._store_viral_post(viral_post)
            
            # Auto-post if user has enabled it
            await self._auto_post_if_enabled(user_address, viral_post)
            
            logger.info(f"🎉 Viral content created for achievement: {achievement_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to process achievement unlock: {e}")
            return False
    
    async def process_tier_upgrade(self, user_address: str, tier_data: Dict) -> bool:
        """Process tier upgrade and create viral content"""
        try:
            tier_name = tier_data['tier']
            apy = tier_data['apy']
            discount = tier_data['gpu_discount']
            boost = tier_data['provider_boost']
            staked_amount = tier_data['staked_amount']
            
            # Generate tier upgrade content
            content = self._generate_viral_content('tier_upgrade', {
                'tier': tier_name,
                'apy': apy,
                'discount': discount,
                'boost': boost,
                'amount': f"{staked_amount:,.0f}"
            })
            
            # Create tier badge image
            image_path = await self._create_tier_badge_image(tier_data)
            
            # Create viral post
            post_id = self._generate_post_id(user_address, f"tier_{tier_name}")
            viral_post = ViralPost(
                id=post_id,
                user_address=user_address,
                platform='twitter',
                content=content,
                image_url=image_path,
                achievement_id=None,
                tier_reached=tier_name,
                engagement_score=0,
                viral_potential=self._calculate_tier_viral_potential(tier_name),
                reward_amount=25.0 if tier_name in ['GOLD', 'DIAMOND'] else 15.0,
                posted_at=time.time(),
                verified=False
            )
            
            await self._store_viral_post(viral_post)
            await self._auto_post_if_enabled(user_address, viral_post)
            
            logger.info(f"💎 Viral content created for tier upgrade: {tier_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to process tier upgrade: {e}")
            return False
    
    def _get_template_key(self, achievement_id: str) -> str:
        """Get appropriate template key for achievement"""
        template_mapping = {
            'first_rental': 'first_rental',
            'power_user': 'achievement_unlock',
            'loyal_customer': 'achievement_unlock',
            'provider_debut': 'provider_earnings',
            'high_rating': 'provider_earnings',
            'referral_bonus': 'referral_success'
        }
        return template_mapping.get(achievement_id, 'achievement_unlock')
    
    def _generate_viral_content(self, template_key: str, data: Dict) -> str:
        """Generate viral content using templates"""
        import random
        
        templates = self.viral_templates.get(template_key, self.viral_templates['achievement_unlock'])
        template = random.choice(templates)
        
        try:
            return template.format(**data)
        except KeyError as e:
            logger.warning(f"Missing template variable {e}, using default")
            return template
    
    async def _create_achievement_image(self, achievement_data: Dict) -> str:
        """Create viral achievement image with GPUDex branding"""
        try:
            # Create achievement badge image
            width, height = 800, 600
            img = Image.new('RGB', (width, height), color='#1a1a2e')
            draw = ImageDraw.Draw(img)
            
            # Load fonts (fallback to default if not available)
            try:
                title_font = ImageFont.truetype("arial.ttf", 48)
                subtitle_font = ImageFont.truetype("arial.ttf", 32)
                reward_font = ImageFont.truetype("arial.ttf", 40)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                reward_font = ImageFont.load_default()
            
            # Draw background gradient effect
            for i in range(height):
                color_val = int(26 + (50 * i / height))
                draw.line([(0, i), (width, i)], fill=(color_val, color_val, 70))
            
            # Draw achievement content
            achievement_name = achievement_data['name']
            reward = achievement_data['reward']
            
            # Achievement icon (using emoji as text)
            draw.text((width//2, 150), "🏆", font=title_font, anchor="mm", fill='#ffd700')
            
            # Achievement name
            draw.text((width//2, 250), achievement_name, font=title_font, anchor="mm", fill='#ffffff')
            
            # Reward amount
            draw.text((width//2, 350), f"+{reward} GPUDX", font=reward_font, anchor="mm", fill='#00ff88')
            
            # GPUDex branding
            draw.text((width//2, 450), "💎 GPUDex Achievement Unlocked! 💎", font=subtitle_font, anchor="mm", fill='#888888')
            
            # Save image
            image_path = f"temp/achievement_{achievement_data['id']}_{int(time.time())}.png"
            os.makedirs('temp', exist_ok=True)
            img.save(image_path)
            
            return image_path
            
        except Exception as e:
            logger.error(f"❌ Failed to create achievement image: {e}")
            return None
    
    async def _create_tier_badge_image(self, tier_data: Dict) -> str:
        """Create tier badge image for social sharing"""
        try:
            # Create tier badge with dynamic colors
            width, height = 800, 600
            
            tier_colors = {
                'BRONZE': '#cd7f32',
                'SILVER': '#c0c0c0', 
                'GOLD': '#ffd700',
                'DIAMOND': '#b9f2ff'
            }
            
            tier_name = tier_data['tier']
            tier_color = tier_colors.get(tier_name, '#ffffff')
            
            img = Image.new('RGB', (width, height), color='#0f0f23')
            draw = ImageDraw.Draw(img)
            
            # Fonts
            try:
                title_font = ImageFont.truetype("arial.ttf", 60)
                stats_font = ImageFont.truetype("arial.ttf", 36)
            except:
                title_font = ImageFont.load_default()
                stats_font = ImageFont.load_default()
            
            # Draw tier badge background
            badge_radius = 150
            center_x, center_y = width//2, height//2 - 50
            
            # Draw tier icon
            tier_icons = {'BRONZE': '🥉', 'SILVER': '🥈', 'GOLD': '🥇', 'DIAMOND': '💎'}
            icon = tier_icons.get(tier_name, '⭐')
            draw.text((center_x, center_y - 80), icon, font=title_font, anchor="mm")
            
            # Draw tier name
            draw.text((center_x, center_y), f"{tier_name} TIER", font=title_font, anchor="mm", fill=tier_color)
            
            # Draw stats
            apy = tier_data['apy']
            discount = tier_data['gpu_discount']
            boost = tier_data['provider_boost']
            
            stats_y = center_y + 80
            draw.text((center_x, stats_y), f"{apy}% APY • {discount}% GPU Discount • +{boost}% Provider Boost", 
                     font=stats_font, anchor="mm", fill='#ffffff')
            
            # GPUDex branding
            draw.text((center_x, height - 80), "💎 GPUDex - Utility-First Tokenomics 💎", 
                     font=stats_font, anchor="mm", fill='#888888')
            
            # Save image
            image_path = f"temp/tier_{tier_name.lower()}_{int(time.time())}.png"
            os.makedirs('temp', exist_ok=True)
            img.save(image_path)
            
            return image_path
            
        except Exception as e:
            logger.error(f"❌ Failed to create tier badge image: {e}")
            return None
    
    def _calculate_viral_potential(self, achievement_data: Dict) -> float:
        """Calculate viral potential score (0-1) based on achievement type"""
        base_scores = {
            'first_rental': 0.6,
            'power_user': 0.8,
            'loyal_customer': 0.7,
            'provider_debut': 0.9,
            'high_rating': 0.8,
            'diamond_elite': 1.0
        }
        
        achievement_id = achievement_data.get('id', 'default')
        base_score = base_scores.get(achievement_id, 0.5)
        
        # Bonus for high reward amounts
        reward = achievement_data.get('reward', 0)
        reward_bonus = min(0.3, reward / 1000)  # +0.3 max for 1000+ reward
        
        return min(1.0, base_score + reward_bonus)
    
    def _calculate_tier_viral_potential(self, tier_name: str) -> float:
        """Calculate viral potential for tier upgrades"""
        tier_scores = {
            'BRONZE': 0.6,
            'SILVER': 0.7,
            'GOLD': 0.9,
            'DIAMOND': 1.0
        }
        return tier_scores.get(tier_name, 0.5)
    
    def _generate_post_id(self, user_address: str, suffix: str) -> str:
        """Generate unique post ID"""
        data = f"{user_address}:{suffix}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def _store_viral_post(self, viral_post: ViralPost):
        """Store viral post in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO viral_posts 
                (id, user_address, platform, content, image_url, achievement_id, tier_reached,
                 engagement_score, viral_potential, reward_amount, posted_at, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                viral_post.id, viral_post.user_address, viral_post.platform, viral_post.content,
                viral_post.image_url, viral_post.achievement_id, viral_post.tier_reached,
                viral_post.engagement_score, viral_post.viral_potential, viral_post.reward_amount,
                viral_post.posted_at, viral_post.verified
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to store viral post: {e}")
    
    async def _auto_post_if_enabled(self, user_address: str, viral_post: ViralPost):
        """Auto-post to social media if user has enabled it"""
        try:
            # Check if user has auto-posting enabled (would be stored in user preferences)
            # For now, we'll just log the content that would be posted
            
            logger.info(f"📱 Auto-post ready for {user_address}:")
            logger.info(f"   Content: {viral_post.content}")
            logger.info(f"   Image: {viral_post.image_url}")
            logger.info(f"   Reward: {viral_post.reward_amount} GPUDX")
            
            # In production, this would actually post to Twitter/Discord/etc.
            # await self._post_to_twitter(viral_post)
            # await self._post_to_discord(viral_post)
            
        except Exception as e:
            logger.error(f"❌ Failed to auto-post: {e}")
    
    async def register_influencer(self, influencer_data: Dict) -> str:
        """Register new influencer with custom referral tracking"""
        try:
            address = influencer_data['address']
            twitter_handle = influencer_data.get('twitter_handle')
            follower_count = influencer_data.get('follower_count', 0)
            
            # Generate custom referral code
            referral_code = self._generate_referral_code(address, twitter_handle)
            
            # Determine influencer tier based on followers
            tier = self._calculate_influencer_tier(follower_count)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO influencers 
                (address, twitter_handle, follower_count, tier, custom_referral_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (address, twitter_handle, follower_count, tier, referral_code))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Influencer registered: {twitter_handle} ({tier} tier)")
            return referral_code
            
        except Exception as e:
            logger.error(f"❌ Failed to register influencer: {e}")
            return None
    
    def _generate_referral_code(self, address: str, twitter_handle: str) -> str:
        """Generate custom referral code for influencer"""
        if twitter_handle:
            base = twitter_handle.replace('@', '').upper()[:6]
        else:
            base = address[:6].upper()
        
        suffix = hashlib.sha256(f"{address}:{twitter_handle}".encode()).hexdigest()[:4].upper()
        return f"{base}{suffix}"
    
    def _calculate_influencer_tier(self, follower_count: int) -> str:
        """Calculate influencer tier based on follower count"""
        if follower_count >= 100000:
            return 'diamond'
        elif follower_count >= 10000:
            return 'gold'
        elif follower_count >= 1000:
            return 'silver'
        else:
            return 'bronze'
    
    async def launch_viral_campaign(self, campaign_data: Dict) -> str:
        """Launch time-limited viral campaign"""
        try:
            campaign_id = hashlib.sha256(f"{campaign_data['name']}:{time.time()}".encode()).hexdigest()[:12]
            
            campaign = ViralCampaign(
                id=campaign_id,
                name=campaign_data['name'],
                start_date=time.time(),
                end_date=time.time() + (campaign_data.get('duration_days', 7) * 24 * 60 * 60),
                target_platform=campaign_data.get('platform', 'twitter'),
                reward_per_share=campaign_data.get('reward_per_share', 25.0),
                bonus_multiplier=campaign_data.get('bonus_multiplier', 2.0),
                hashtags=campaign_data.get('hashtags', ['#GPUDX', '#GPU', '#DeFi']),
                target_engagement=campaign_data.get('target_engagement', 10000),
                current_participants=0,
                total_rewards_distributed=0,
                active=True
            )
            
            # Store campaign
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO viral_campaigns 
                (id, name, start_date, end_date, target_platform, reward_per_share,
                 bonus_multiplier, hashtags, target_engagement, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                campaign.id, campaign.name, campaign.start_date, campaign.end_date,
                campaign.target_platform, campaign.reward_per_share, campaign.bonus_multiplier,
                json.dumps(campaign.hashtags), campaign.target_engagement, campaign.active
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"🚀 Viral campaign launched: {campaign.name}")
            return campaign_id
            
        except Exception as e:
            logger.error(f"❌ Failed to launch viral campaign: {e}")
            return None
    
    async def get_viral_leaderboard(self, period_days: int = 7) -> List[Dict]:
        """Get viral engagement leaderboard"""
        try:
            cutoff_time = time.time() - (period_days * 24 * 60 * 60)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_address, COUNT(*) as posts, SUM(engagement_score) as total_engagement,
                       SUM(reward_amount) as total_rewards, AVG(viral_potential) as avg_viral_score
                FROM viral_posts 
                WHERE posted_at > ? AND verified = TRUE
                GROUP BY user_address
                ORDER BY total_engagement DESC
                LIMIT 50
            ''', (cutoff_time,))
            
            leaderboard = []
            for row in cursor.fetchall():
                leaderboard.append({
                    'address': row[0],
                    'posts': row[1],
                    'engagement': row[2],
                    'rewards': row[3],
                    'viral_score': row[4],
                    'rank': len(leaderboard) + 1
                })
            
            conn.close()
            return leaderboard
            
        except Exception as e:
            logger.error(f"❌ Failed to get viral leaderboard: {e}")
            return []
    
    async def get_viral_analytics(self) -> Dict:
        """Get comprehensive viral marketing analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total posts and engagement
            cursor.execute('SELECT COUNT(*), SUM(engagement_score), SUM(reward_amount) FROM viral_posts WHERE verified = TRUE')
            total_posts, total_engagement, total_rewards = cursor.fetchone()
            
            # Posts by platform
            cursor.execute('SELECT platform, COUNT(*) FROM viral_posts GROUP BY platform')
            platform_breakdown = dict(cursor.fetchall())
            
            # Top performing content types
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN achievement_id IS NOT NULL THEN 'achievement'
                        WHEN tier_reached IS NOT NULL THEN 'tier_upgrade'
                        ELSE 'general'
                    END as content_type,
                    COUNT(*), AVG(engagement_score), AVG(viral_potential)
                FROM viral_posts 
                WHERE verified = TRUE
                GROUP BY content_type
            ''')
            content_performance = cursor.fetchall()
            
            # Active campaigns
            cursor.execute('SELECT COUNT(*) FROM viral_campaigns WHERE active = TRUE')
            active_campaigns = cursor.fetchone()[0]
            
            # Influencer count by tier
            cursor.execute('SELECT tier, COUNT(*) FROM influencers GROUP BY tier')
            influencer_tiers = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_viral_posts': total_posts or 0,
                'total_engagement': total_engagement or 0,
                'total_rewards_distributed': total_rewards or 0,
                'platform_breakdown': platform_breakdown,
                'content_performance': [
                    {
                        'type': row[0],
                        'count': row[1],
                        'avg_engagement': row[2],
                        'avg_viral_score': row[3]
                    } for row in content_performance
                ],
                'active_campaigns': active_campaigns,
                'influencer_breakdown': influencer_tiers,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get viral analytics: {e}")
            return {}

# Example usage and testing
async def main():
    """Test the viral marketing engine"""
    config = {
        'database_path': 'viral_marketing.db',
        'twitter_api_key': 'your_key',
        'twitter_api_secret': 'your_secret',
        'twitter_access_token': 'your_token',
        'twitter_access_secret': 'your_token_secret',
        'discord_webhook_url': 'your_webhook_url'
    }
    
    engine = ViralMarketingEngine(config)
    
    # Test achievement unlock
    achievement_data = {
        'id': 'power_user',
        'name': 'GPU Power User',
        'description': 'Completed 100+ hours of GPU rentals',
        'reward': 200
    }
    
    await engine.process_achievement_unlock('0x1234...', achievement_data)
    
    # Test tier upgrade
    tier_data = {
        'tier': 'GOLD',
        'apy': 15,
        'gpu_discount': 15,
        'provider_boost': 15,
        'staked_amount': 100000
    }
    
    await engine.process_tier_upgrade('0x1234...', tier_data)
    
    # Get analytics
    analytics = await engine.get_viral_analytics()
    print("Viral Analytics:", json.dumps(analytics, indent=2))

if __name__ == "__main__":
    print("🔥 Viral Marketing Engine Test - MAXIMUM VIRAL VELOCITY! 🔥")
    asyncio.run(main()) 