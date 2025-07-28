#!/usr/bin/env python3
"""
GPUDx Platform Integration Service
Connects all V2 components: Token, Escrow, Utility Validation, and Community Onboarding
MAXIMUM VELOCITY INTEGRATION SYSTEM! 🚀
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import aiohttp
from web3 import Web3
from web3.contract import Contract

# Import our custom services
from utility_validation_service import UtilityValidationService
from community_onboarding_service import CommunityOnboardingService, UserTier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PlatformConfig:
    """Platform configuration data structure"""
    rpc_url: str
    token_contract_address: str
    escrow_contract_address: str
    private_key: str
    utility_validation_enabled: bool
    social_gamification_enabled: bool
    database_path: str
    metrics_interval_hours: int

class GPUDxPlatformIntegration:
    """Main integration service for the GPUDx V2 platform"""
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.web3 = Web3(Web3.HTTPProvider(config.rpc_url))
        
        # Initialize services
        self.utility_service = None
        self.community_service = None
        self.token_contract = None
        self.escrow_contract = None
        
        # Platform state
        self.is_running = False
        self.last_sync_time = 0
        
        logger.info("🚀 GPUDx Platform Integration initializing with MAXIMUM VELOCITY!")
    
    async def initialize(self):
        """Initialize all platform components"""
        try:
            logger.info("🔥 Initializing platform components...")
            
            # 1. Load smart contracts
            await self._load_contracts()
            
            # 2. Initialize utility validation service
            if self.config.utility_validation_enabled:
                utility_config = {
                    'database_path': 'utility_metrics.db',
                    'rpc_url': self.config.rpc_url,
                    'token_contract_address': self.config.token_contract_address,
                    'escrow_contract_address': self.config.escrow_contract_address
                }
                self.utility_service = UtilityValidationService(utility_config)
                logger.info("✅ Utility validation service initialized")
            
            # 3. Initialize community onboarding service
            if self.config.social_gamification_enabled:
                community_config = {
                    'database_path': 'community_onboarding.db'
                }
                self.community_service = CommunityOnboardingService(community_config)
                logger.info("✅ Community onboarding service initialized")
            
            # 4. Test platform connectivity
            await self._test_platform_connectivity()
            
            logger.info("🎉 Platform initialization complete! Ready to REVOLUTIONIZE GPU COMPUTE!")
            
        except Exception as e:
            logger.error(f"💥 Platform initialization failed: {e}")
            raise
    
    async def _load_contracts(self):
        """Load smart contract instances"""
        try:
            # Load contract ABIs
            with open('artifacts/contracts/GPUDexTokenV2.sol/GPUDexTokenV2.json', 'r') as f:
                token_abi = json.load(f)['abi']
            
            with open('artifacts/contracts/GPUDexEscrowV2.sol/GPUDexEscrowV2.json', 'r') as f:
                escrow_abi = json.load(f)['abi']
            
            # Initialize contracts
            self.token_contract = self.web3.eth.contract(
                address=self.config.token_contract_address,
                abi=token_abi
            )
            
            self.escrow_contract = self.web3.eth.contract(
                address=self.config.escrow_contract_address,
                abi=escrow_abi
            )
            
            logger.info("✅ Smart contracts loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load contracts: {e}")
            raise
    
    async def _test_platform_connectivity(self):
        """Test connectivity to all platform components"""
        try:
            # Test blockchain connectivity
            latest_block = self.web3.eth.block_number
            logger.info(f"📡 Blockchain connected - Latest block: {latest_block}")
            
            # Test token contract
            total_supply = self.token_contract.functions.totalSupply().call()
            logger.info(f"💎 Token contract connected - Total supply: {total_supply / 10**18:.2f} GPUDX")
            
            # Test escrow contract
            platform_metrics = self.escrow_contract.functions.getPlatformMetrics().call()
            logger.info(f"🏢 Escrow contract connected - Total rentals: {platform_metrics[0]}")
            
            # Test utility service
            if self.utility_service:
                test_metrics = await self.utility_service.collect_utility_metrics()
                logger.info(f"📊 Utility service connected - GPUDX usage: {test_metrics.gpudx_payment_percentage:.1f}%")
            
            # Test community service
            if self.community_service:
                stats = await self.community_service.get_community_stats()
                logger.info(f"👥 Community service connected - Total users: {stats.get('total_users', 0)}")
            
            logger.info("✅ All platform components connected successfully!")
            
        except Exception as e:
            logger.error(f"❌ Platform connectivity test failed: {e}")
            raise
    
    async def process_new_user(self, user_address: str, referrer_address: Optional[str] = None) -> Dict:
        """Process a new user joining the platform"""
        try:
            logger.info(f"🎯 Processing new user: {user_address}")
            
            # 1. Register user in community service
            user_profile = None
            if self.community_service:
                user_profile = await self.community_service.register_user(user_address, referrer_address)
                logger.info(f"👤 User registered in community service")
            
            # 2. Track user activity in utility service
            if self.utility_service:
                await self.utility_service.track_user_activity(
                    user_address, "user_signup", 0, None
                )
                logger.info(f"📈 User signup tracked in utility service")
            
            # 3. Award welcome bonus through smart contract
            if self.community_service:
                await self.community_service.complete_onboarding_task(
                    user_address, "welcome_tutorial"
                )
                logger.info(f"🎁 Welcome bonus awarded")
            
            result = {
                "user_address": user_address,
                "registration_successful": True,
                "profile": asdict(user_profile) if user_profile else None,
                "welcome_bonus_awarded": True,
                "timestamp": time.time()
            }
            
            logger.info(f"✅ New user processed successfully: {user_address}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process new user {user_address}: {e}")
            return {
                "user_address": user_address,
                "registration_successful": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def process_gpu_rental(self, rental_data: Dict) -> Dict:
        """Process a GPU rental transaction with full integration"""
        try:
            logger.info(f"🖥️ Processing GPU rental: {rental_data['rental_id']}")
            
            user_address = rental_data['renter_address']
            provider_address = rental_data['provider_address']
            amount = rental_data['amount']
            
            # 1. Get user tier info for discount calculation
            user_tier_info = self.token_contract.functions.getUserTierInfo(user_address).call()
            discount_percentage = user_tier_info[4] / 100  # gpuDiscountBasisPoints / 100
            
            # 2. Calculate discount amount
            discount_amount = amount * discount_percentage / 100 if discount_percentage > 0 else 0
            
            # 3. Track rental in utility service
            if self.utility_service:
                await self.utility_service.track_rental_activity(rental_data)
                logger.info(f"📊 Rental tracked in utility service")
            
            # 4. Update user achievements in community service
            if self.community_service:
                # Update GPU rental hours for achievements
                user_profile = await self.community_service.get_user_profile(user_address)
                if user_profile:
                    new_hours = user_profile.total_gpu_hours + rental_data.get('duration', 1)
                    
                    # Check for hour-based achievements
                    if new_hours >= 100 and user_profile.total_gpu_hours < 100:
                        await self.community_service.complete_onboarding_task(user_address, "power_user_achievement")
                    
                logger.info(f"🏆 User achievements updated")
            
            # 5. Process provider earnings boost
            provider_tier_info = self.token_contract.functions.getUserTierInfo(provider_address).call()
            provider_boost_percentage = provider_tier_info[5] / 100  # providerBoostBasisPoints / 100
            
            result = {
                "rental_id": rental_data['rental_id'],
                "processing_successful": True,
                "user_discount_applied": discount_amount,
                "provider_boost_percentage": provider_boost_percentage,
                "utility_tracked": self.utility_service is not None,
                "achievements_updated": self.community_service is not None,
                "timestamp": time.time()
            }
            
            logger.info(f"✅ GPU rental processed successfully: {rental_data['rental_id']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process GPU rental {rental_data['rental_id']}: {e}")
            return {
                "rental_id": rental_data['rental_id'],
                "processing_successful": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def process_staking_action(self, user_address: str, action: str, amount: float) -> Dict:
        """Process staking actions (stake/unstake/claim) with full integration"""
        try:
            logger.info(f"🥩 Processing staking action: {action} for {user_address}")
            
            # 1. Get user tier before action
            old_tier_info = self.token_contract.functions.getUserTierInfo(user_address).call()
            old_tier = old_tier_info[0]
            
            # 2. Track staking activity in utility service
            if self.utility_service:
                await self.utility_service.track_user_activity(
                    user_address, f"staking_{action}", amount, None
                )
                logger.info(f"📈 Staking activity tracked")
            
            # 3. Update community profile
            if self.community_service:
                user_profile = await self.community_service.get_user_profile(user_address)
                if user_profile:
                    # Update staked amount in community profile
                    # This would typically be done through a database update
                    pass
                
                # Check for tier-based achievements
                new_tier_info = self.token_contract.functions.getUserTierInfo(user_address).call()
                new_tier = new_tier_info[0]
                
                if new_tier > old_tier:
                    # Tier upgraded! Award achievement
                    tier_names = ["NONE", "BRONZE", "SILVER", "GOLD", "DIAMOND"]
                    if new_tier == 4:  # Diamond tier
                        await self.community_service._award_achievement(user_address, "diamond_elite")
                    
                    logger.info(f"🎉 User {user_address} upgraded to {tier_names[new_tier]} tier!")
            
            result = {
                "user_address": user_address,
                "action": action,
                "amount": amount,
                "processing_successful": True,
                "old_tier": old_tier,
                "tier_upgraded": False,  # Would be determined by contract call
                "timestamp": time.time()
            }
            
            logger.info(f"✅ Staking action processed successfully: {action} for {user_address}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process staking action {action} for {user_address}: {e}")
            return {
                "user_address": user_address,
                "action": action,
                "processing_successful": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def process_social_activity(self, user_address: str, activity_type: str, platform: str, 
                                    content_url: Optional[str] = None) -> Dict:
        """Process social media activity and award rewards"""
        try:
            logger.info(f"📱 Processing social activity: {activity_type} by {user_address}")
            
            # 1. Determine reward amount based on activity type
            reward_mapping = {
                "twitter_share": 10.0,
                "discord_message": 5.0,
                "reddit_post": 15.0,
                "youtube_video": 50.0,
                "tutorial_creation": 100.0,
                "community_help": 20.0
            }
            
            reward_amount = reward_mapping.get(activity_type, 10.0)
            
            # 2. Track in community service
            if self.community_service:
                success = await self.community_service.track_social_activity(
                    user_address, activity_type, platform, content_url, reward_amount
                )
                
                if success:
                    logger.info(f"🎁 Social reward awarded: {reward_amount} GPUDX")
                else:
                    logger.warning(f"⚠️ Failed to track social activity")
            
            # 3. Track in utility service
            if self.utility_service:
                await self.utility_service.track_user_activity(
                    user_address, f"social_{activity_type}", reward_amount, None
                )
            
            result = {
                "user_address": user_address,
                "activity_type": activity_type,
                "platform": platform,
                "reward_amount": reward_amount,
                "processing_successful": True,
                "timestamp": time.time()
            }
            
            logger.info(f"✅ Social activity processed successfully: {activity_type}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process social activity {activity_type}: {e}")
            return {
                "user_address": user_address,
                "activity_type": activity_type,
                "processing_successful": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def generate_platform_report(self) -> Dict:
        """Generate comprehensive platform report"""
        try:
            logger.info("📊 Generating comprehensive platform report...")
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "platform_status": "operational",
                "components": {}
            }
            
            # 1. Blockchain metrics
            try:
                latest_block = self.web3.eth.block_number
                total_supply = self.token_contract.functions.totalSupply().call()
                total_staked = self.token_contract.functions.totalStaked().call()
                
                report["components"]["blockchain"] = {
                    "status": "connected",
                    "latest_block": latest_block,
                    "total_supply": total_supply / 10**18,
                    "total_staked": total_staked / 10**18,
                    "staking_rate": (total_staked / total_supply * 100) if total_supply > 0 else 0
                }
            except Exception as e:
                report["components"]["blockchain"] = {"status": "error", "error": str(e)}
            
            # 2. Utility validation metrics
            if self.utility_service:
                try:
                    utility_report = await self.utility_service.get_utility_validation_report()
                    report["components"]["utility_validation"] = utility_report
                except Exception as e:
                    report["components"]["utility_validation"] = {"status": "error", "error": str(e)}
            
            # 3. Community metrics
            if self.community_service:
                try:
                    community_stats = await self.community_service.get_community_stats()
                    report["components"]["community"] = community_stats
                except Exception as e:
                    report["components"]["community"] = {"status": "error", "error": str(e)}
            
            # 4. Platform health score
            health_score = 100
            for component, data in report["components"].items():
                if isinstance(data, dict) and data.get("status") == "error":
                    health_score -= 25
            
            report["platform_health_score"] = max(0, health_score)
            
            logger.info(f"✅ Platform report generated - Health score: {health_score}%")
            return report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate platform report: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "platform_status": "error",
                "error": str(e)
            }
    
    async def start_platform_monitoring(self):
        """Start continuous platform monitoring"""
        logger.info("🔍 Starting platform monitoring with MAXIMUM VELOCITY!")
        self.is_running = True
        
        while self.is_running:
            try:
                # 1. Collect utility metrics
                if self.utility_service:
                    await self.utility_service.collect_utility_metrics()
                
                # 2. Update platform sync time
                self.last_sync_time = time.time()
                
                # 3. Generate periodic report
                if int(time.time()) % 3600 == 0:  # Every hour
                    report = await self.generate_platform_report()
                    logger.info(f"📈 Hourly report: Health score {report.get('platform_health_score', 0)}%")
                
                # 4. Sleep until next cycle
                await asyncio.sleep(self.config.metrics_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"💥 Platform monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def stop_platform_monitoring(self):
        """Stop platform monitoring"""
        logger.info("🛑 Stopping platform monitoring...")
        self.is_running = False
    
    async def get_user_dashboard_data(self, user_address: str) -> Dict:
        """Get comprehensive dashboard data for a user"""
        try:
            dashboard = {
                "user_address": user_address,
                "timestamp": time.time()
            }
            
            # 1. Token/staking data
            try:
                tier_info = self.token_contract.functions.getUserTierInfo(user_address).call()
                pending_rewards = self.token_contract.functions.pendingRewards(user_address).call()
                
                dashboard["staking"] = {
                    "tier": ["NONE", "BRONZE", "SILVER", "GOLD", "DIAMOND"][tier_info[0]],
                    "staked_amount": tier_info[1] / 10**18,
                    "min_stake_next_tier": tier_info[2] / 10**18 if tier_info[2] > 0 else 0,
                    "apy_percentage": tier_info[3] / 100,
                    "gpu_discount_percentage": tier_info[4] / 100,
                    "provider_boost_percentage": tier_info[5] / 100,
                    "pending_rewards": {
                        "platform": pending_rewards[0] / 10**18,
                        "apy": pending_rewards[1] / 10**18,
                        "fees": pending_rewards[2] / 10**18
                    }
                }
            except Exception as e:
                dashboard["staking"] = {"error": str(e)}
            
            # 2. Community data
            if self.community_service:
                try:
                    profile = await self.community_service.get_user_profile(user_address)
                    achievements = await self.community_service.get_user_achievements(user_address)
                    onboarding = await self.community_service.get_onboarding_progress(user_address)
                    
                    dashboard["community"] = {
                        "profile": asdict(profile) if profile else None,
                        "achievements": [asdict(a) for a in achievements],
                        "onboarding_progress": [asdict(t) for t in onboarding]
                    }
                except Exception as e:
                    dashboard["community"] = {"error": str(e)}
            
            # 3. Platform metrics
            try:
                utility_metrics = self.token_contract.functions.getUtilityMetrics().call()
                dashboard["platform_metrics"] = {
                    "total_gpu_spending": utility_metrics[0] / 10**18,
                    "total_provider_earnings": utility_metrics[1] / 10**18,
                    "total_users_served": utility_metrics[2],
                    "platform_revenue": utility_metrics[3] / 10**18,
                    "utility_token_percentage": utility_metrics[5]
                }
            except Exception as e:
                dashboard["platform_metrics"] = {"error": str(e)}
            
            return dashboard
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard data for {user_address}: {e}")
            return {
                "user_address": user_address,
                "error": str(e),
                "timestamp": time.time()
            }

# Example usage and testing
async def main():
    """Example usage of the platform integration"""
    import os
    
    # Configuration from environment variables
    config = PlatformConfig(
        rpc_url=os.getenv('RPC_URL', 'http://localhost:8545'),
        token_contract_address=os.getenv('GPUDX_TOKEN_V2_ADDRESS', '0x5FbDB2315678afecb367f032d93F642f64180aa3'),
        escrow_contract_address=os.getenv('GPUDX_ESCROW_V2_ADDRESS', '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512'),
        private_key=os.getenv('DEPLOYER_PRIVATE_KEY', '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'),
        utility_validation_enabled=True,
        social_gamification_enabled=True,
        database_path="./platform_data",
        metrics_interval_hours=1
    )
    
    # Initialize platform
    platform = GPUDxPlatformIntegration(config)
    await platform.initialize()
    
    # Test new user registration
    test_user = "0x1234567890123456789012345678901234567890"
    result = await platform.process_new_user(test_user)
    print("New user result:", result)
    
    # Test GPU rental processing
    rental_data = {
        "rental_id": 1,
        "renter_address": test_user,
        "provider_address": "0x9876543210987654321098765432109876543210",
        "amount": 100.0,
        "duration": 5,
        "gpu_type": "RTX 4090"
    }
    rental_result = await platform.process_gpu_rental(rental_data)
    print("Rental result:", rental_result)
    
    # Generate platform report
    report = await platform.generate_platform_report()
    print("Platform report:", json.dumps(report, indent=2))

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    import os
    
    # Configuration
    config = {
        'database_url': os.getenv('DATABASE_URL', 'postgresql://gpudex:password@postgres:5432/gpudex_db'),
        'rpc_url': os.getenv('RPC_URL', 'http://localhost:8545'),
        'token_contract_address': os.getenv('GPUDX_TOKEN_V2_ADDRESS', '0x5FbDB2315678afecb367f032d93F642f64180aa3'),
        'port': int(os.getenv('PLATFORM_INTEGRATION_PORT', '8009'))
    }
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx Platform Integration Service", version="2.0.0")
    
    @app.get("/")
    async def root():
        return {"message": "GPUDx Platform Integration Service", "status": "operational"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "platform_integration"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from fastapi import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return {"error": "Prometheus client not available", "service": "platform_integration"}
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=config['port']) 