#!/usr/bin/env python3
"""
GPUDex Utility Validation Service
Tracks and validates token utility metrics for the GPUDX ecosystem
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
from web3 import Web3
from web3.contract import Contract

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UtilityMetrics:
    """Core utility validation metrics"""
    timestamp: float
    
    # Token Usage Metrics
    total_gpu_spending: float
    gpudx_payment_percentage: float
    staking_participation_rate: float
    token_velocity: float
    
    # Platform Activity Metrics  
    daily_active_users: int
    monthly_active_users: int
    gpu_rental_volume: float
    provider_earnings: float
    
    # Utility Validation Metrics
    discount_utilization_rate: float
    staking_tier_distribution: Dict[str, int]
    social_reward_distribution: float
    referral_adoption_rate: float
    
    # Business Performance Metrics
    platform_revenue: float
    enterprise_adoption: int
    provider_retention_rate: float
    user_retention_rate: float
    
    # Token Economics Health
    burn_rate: float
    inflation_rate: float
    yield_sustainability_score: float
    utility_demand_score: float

class UtilityValidationService:
    """Service for tracking and validating token utility across the platform"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_path = config.get('database_path', 'utility_metrics.db')
        self.web3 = Web3(Web3.HTTPProvider(config['rpc_url']))
        self.token_contract = None
        self.escrow_contract = None
        self.metrics_history = []
        
        # Initialize database
        self._init_database()
        
        # Load contract ABIs and addresses
        self._load_contracts()
    
    def _init_database(self):
        """Initialize SQLite database for metrics storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utility_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                metrics_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user activity table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_address TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                amount REAL,
                timestamp REAL NOT NULL,
                block_number INTEGER,
                transaction_hash TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create staking activity table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staking_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_address TEXT NOT NULL,
                action TEXT NOT NULL, -- 'stake', 'unstake', 'claim_rewards'
                amount REAL NOT NULL,
                tier TEXT,
                timestamp REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create rental activity table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rental_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rental_id INTEGER NOT NULL,
                renter_address TEXT NOT NULL,
                provider_address TEXT NOT NULL,
                gpu_type TEXT,
                amount REAL NOT NULL,
                discount_applied REAL DEFAULT 0,
                paid_with_gpudx BOOLEAN DEFAULT FALSE,
                performance_score INTEGER,
                timestamp REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def _load_contracts(self):
        """Load smart contract instances"""
        try:
            # Load GPUDexTokenV2 contract
            with open('artifacts/contracts/GPUDexTokenV2.sol/GPUDexTokenV2.json', 'r') as f:
                token_abi = json.load(f)['abi']
            
            self.token_contract = self.web3.eth.contract(
                address=self.config['token_contract_address'],
                abi=token_abi
            )
            
            # Load GPUDexEscrowV2 contract
            with open('artifacts/contracts/GPUDexEscrowV2.sol/GPUDexEscrowV2.json', 'r') as f:
                escrow_abi = json.load(f)['abi']
            
            self.escrow_contract = self.web3.eth.contract(
                address=self.config['escrow_contract_address'],
                abi=escrow_abi
            )
            
            logger.info("Smart contracts loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load contracts: {e}")
            raise
    
    async def collect_utility_metrics(self) -> UtilityMetrics:
        """Collect comprehensive utility metrics from all sources"""
        timestamp = time.time()
        
        # Collect on-chain metrics
        token_metrics = await self._collect_token_metrics()
        platform_metrics = await self._collect_platform_metrics()
        staking_metrics = await self._collect_staking_metrics()
        
        # Collect off-chain metrics from database
        user_metrics = await self._collect_user_metrics()
        business_metrics = await self._collect_business_metrics()
        
        # Calculate derived metrics
        utility_scores = await self._calculate_utility_scores(
            token_metrics, platform_metrics, staking_metrics, user_metrics
        )
        
        metrics = UtilityMetrics(
            timestamp=timestamp,
            **token_metrics,
            **platform_metrics,
            **staking_metrics,
            **user_metrics,
            **business_metrics,
            **utility_scores
        )
        
        # Store metrics in database
        await self._store_metrics(metrics)
        
        # Add to in-memory history (keep last 1000 entries)
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 1000:
            self.metrics_history.pop(0)
        
        logger.info(f"Collected utility metrics: {metrics.gpudx_payment_percentage:.1f}% GPUDX usage")
        return metrics
    
    async def _collect_token_metrics(self) -> Dict:
        """Collect token-specific metrics from smart contract"""
        try:
            total_supply = self.token_contract.functions.totalSupply().call()
            total_staked = self.token_contract.functions.totalStaked().call()
            platform_revenue = self.token_contract.functions.platformRevenueGenerated().call()
            
            # Get utility metrics from contract
            utility_data = self.token_contract.functions.getUtilityMetrics().call()
            total_gpu_spending = utility_data[0]
            total_provider_earnings = utility_data[1]
            total_users_served = utility_data[2]
            platform_revenue_generated = utility_data[3]
            total_staked_tokens = utility_data[4]
            utility_token_percentage = utility_data[5]
            
            # Calculate token metrics
            staking_participation_rate = (total_staked / total_supply) * 100 if total_supply > 0 else 0
            token_velocity = await self._calculate_token_velocity()
            
            return {
                'total_gpu_spending': total_gpu_spending / 10**18,
                'staking_participation_rate': staking_participation_rate,
                'token_velocity': token_velocity,
            }
            
        except Exception as e:
            logger.error(f"Error collecting token metrics: {e}")
            return {
                'total_gpu_spending': 0,
                'staking_participation_rate': 0,
                'token_velocity': 0,
            }
    
    async def _collect_platform_metrics(self) -> Dict:
        """Collect platform activity metrics from escrow contract"""
        try:
            # Get platform metrics from escrow contract
            platform_data = self.escrow_contract.functions.getPlatformMetrics().call()
            total_rentals = platform_data[0]
            total_volume = platform_data[1]
            total_discounts = platform_data[2]
            gpudx_utilization_rate = platform_data[3]
            avg_satisfaction = platform_data[4]
            verified_providers = platform_data[5]
            active_users = platform_data[6]
            
            # Calculate percentage of payments made with GPUDX
            gpudx_payment_percentage = gpudx_utilization_rate
            discount_utilization_rate = (total_discounts / total_volume * 100) if total_volume > 0 else 0
            
            return {
                'gpu_rental_volume': total_volume / 10**18,
                'gpudx_payment_percentage': gpudx_payment_percentage,
                'discount_utilization_rate': discount_utilization_rate,
                'daily_active_users': active_users,  # Simplified
                'monthly_active_users': active_users * 30,  # Simplified
            }
            
        except Exception as e:
            logger.error(f"Error collecting platform metrics: {e}")
            return {
                'gpu_rental_volume': 0,
                'gpudx_payment_percentage': 0,
                'discount_utilization_rate': 0,
                'daily_active_users': 0,
                'monthly_active_users': 0,
            }
    
    async def _collect_staking_metrics(self) -> Dict:
        """Collect staking tier distribution and related metrics"""
        try:
            # Get staking tier distribution (would need to be implemented in contract or tracked off-chain)
            tier_distribution = {
                'bronze': 0,
                'silver': 0,
                'gold': 0,
                'diamond': 0
            }
            
            # For now, return simplified metrics
            return {
                'staking_tier_distribution': tier_distribution,
                'provider_earnings': 0,  # Would be calculated from contract events
            }
            
        except Exception as e:
            logger.error(f"Error collecting staking metrics: {e}")
            return {
                'staking_tier_distribution': {'bronze': 0, 'silver': 0, 'gold': 0, 'diamond': 0},
                'provider_earnings': 0,
            }
    
    async def _collect_user_metrics(self) -> Dict:
        """Collect user activity metrics from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate social reward distribution (last 30 days)
            thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
            cursor.execute('''
                SELECT SUM(amount) FROM user_activity 
                WHERE activity_type = 'social_reward' AND timestamp > ?
            ''', (thirty_days_ago,))
            
            social_rewards = cursor.fetchone()[0] or 0
            
            # Calculate referral adoption rate
            cursor.execute('SELECT COUNT(DISTINCT user_address) FROM user_activity WHERE activity_type = "referral"')
            total_referrals = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COUNT(DISTINCT user_address) FROM user_activity')
            total_users = cursor.fetchone()[0] or 1
            
            referral_adoption_rate = (total_referrals / total_users) * 100
            
            conn.close()
            
            return {
                'social_reward_distribution': social_rewards,
                'referral_adoption_rate': referral_adoption_rate,
            }
            
        except Exception as e:
            logger.error(f"Error collecting user metrics: {e}")
            return {
                'social_reward_distribution': 0,
                'referral_adoption_rate': 0,
            }
    
    async def _collect_business_metrics(self) -> Dict:
        """Collect business performance metrics"""
        try:
            # These would come from your business analytics system
            return {
                'platform_revenue': 0,  # From payment processing
                'enterprise_adoption': 0,  # Number of enterprise clients
                'provider_retention_rate': 85.0,  # Percentage
                'user_retention_rate': 72.0,  # Percentage
            }
            
        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}")
            return {
                'platform_revenue': 0,
                'enterprise_adoption': 0,
                'provider_retention_rate': 0,
                'user_retention_rate': 0,
            }
    
    async def _calculate_utility_scores(self, token_metrics: Dict, platform_metrics: Dict, 
                                      staking_metrics: Dict, user_metrics: Dict) -> Dict:
        """Calculate derived utility validation scores"""
        
        # Calculate burn rate (tokens burned per day)
        burn_rate = 0  # Would track from burn events
        
        # Calculate inflation rate (new tokens minted per day)  
        inflation_rate = 0  # Would track from mint events
        
        # Calculate yield sustainability score (0-100)
        staking_rate = token_metrics.get('staking_participation_rate', 0)
        revenue_rate = platform_metrics.get('gpu_rental_volume', 0)
        yield_sustainability = min(100, (staking_rate + revenue_rate) / 2)
        
        # Calculate utility demand score (0-100)
        payment_usage = platform_metrics.get('gpudx_payment_percentage', 0)
        discount_usage = platform_metrics.get('discount_utilization_rate', 0)
        utility_demand = min(100, (payment_usage + discount_usage) / 2)
        
        return {
            'burn_rate': burn_rate,
            'inflation_rate': inflation_rate,
            'yield_sustainability_score': yield_sustainability,
            'utility_demand_score': utility_demand,
        }
    
    async def _calculate_token_velocity(self) -> float:
        """Calculate token velocity (simplified version)"""
        try:
            # Token velocity = Transaction Volume / Average Token Supply
            # This is a simplified calculation
            return 1.5  # Placeholder
            
        except Exception as e:
            logger.error(f"Error calculating token velocity: {e}")
            return 0
    
    async def _store_metrics(self, metrics: UtilityMetrics):
        """Store metrics in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metrics_json = json.dumps(asdict(metrics))
            cursor.execute(
                'INSERT INTO utility_metrics (timestamp, metrics_json) VALUES (?, ?)',
                (metrics.timestamp, metrics_json)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    async def track_user_activity(self, user_address: str, activity_type: str, 
                                amount: float = 0, transaction_hash: str = None):
        """Track individual user activity for utility validation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_activity 
                (user_address, activity_type, amount, timestamp, transaction_hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_address, activity_type, amount, time.time(), transaction_hash))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Tracked activity: {activity_type} for {user_address}")
            
        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")
    
    async def track_rental_activity(self, rental_data: Dict):
        """Track GPU rental activity for utility validation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO rental_activity 
                (rental_id, renter_address, provider_address, gpu_type, amount, 
                 discount_applied, paid_with_gpudx, performance_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rental_data['rental_id'],
                rental_data['renter_address'],
                rental_data['provider_address'],
                rental_data['gpu_type'],
                rental_data['amount'],
                rental_data.get('discount_applied', 0),
                rental_data.get('paid_with_gpudx', False),
                rental_data.get('performance_score', 0),
                time.time()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Tracked rental: {rental_data['rental_id']}")
            
        except Exception as e:
            logger.error(f"Error tracking rental activity: {e}")
    
    async def get_utility_validation_report(self, days: int = 30) -> Dict:
        """Generate comprehensive utility validation report"""
        try:
            if not self.metrics_history:
                await self.collect_utility_metrics()
            
            recent_metrics = self.metrics_history[-1] if self.metrics_history else None
            if not recent_metrics:
                return {"error": "No metrics available"}
            
            # Get historical data
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            historical_data = [m for m in self.metrics_history if m.timestamp > cutoff_time]
            
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "period_days": days,
                "current_metrics": asdict(recent_metrics),
                "validation_status": {
                    "utility_proven": recent_metrics.gpudx_payment_percentage > 25,
                    "staking_healthy": recent_metrics.staking_participation_rate > 30,
                    "platform_growing": recent_metrics.gpu_rental_volume > 0,
                    "user_retention_good": recent_metrics.user_retention_rate > 60
                },
                "trends": self._calculate_trends(historical_data),
                "recommendations": self._generate_recommendations(recent_metrics)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating utility validation report: {e}")
            return {"error": str(e)}
    
    def _calculate_trends(self, historical_data: List[UtilityMetrics]) -> Dict:
        """Calculate trends from historical data"""
        if len(historical_data) < 2:
            return {"insufficient_data": True}
        
        latest = historical_data[-1]
        earliest = historical_data[0]
        
        return {
            "gpudx_usage_trend": latest.gpudx_payment_percentage - earliest.gpudx_payment_percentage,
            "staking_trend": latest.staking_participation_rate - earliest.staking_participation_rate,
            "volume_trend": latest.gpu_rental_volume - earliest.gpu_rental_volume,
            "user_growth_trend": latest.daily_active_users - earliest.daily_active_users
        }
    
    def _generate_recommendations(self, metrics: UtilityMetrics) -> List[str]:
        """Generate recommendations based on current metrics"""
        recommendations = []
        
        if metrics.gpudx_payment_percentage < 30:
            recommendations.append("Increase GPUDX payment incentives - current usage is below target")
        
        if metrics.staking_participation_rate < 40:
            recommendations.append("Enhance staking rewards to improve participation rate")
        
        if metrics.discount_utilization_rate < 50:
            recommendations.append("Promote staking benefits to increase discount utilization")
        
        if metrics.user_retention_rate < 70:
            recommendations.append("Implement user retention programs and improve platform experience")
        
        if metrics.yield_sustainability_score < 60:
            recommendations.append("Review yield mechanisms for long-term sustainability")
        
        return recommendations
    
    async def start_monitoring(self):
        """Start continuous utility monitoring"""
        logger.info("Starting utility validation monitoring...")
        
        while True:
            try:
                await self.collect_utility_metrics()
                await asyncio.sleep(3600)  # Collect metrics every hour
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Example usage and configuration
if __name__ == "__main__":
    import os
    config = {
        'database_path': 'utility_metrics.db',
        'rpc_url': os.getenv('RPC_URL', 'http://localhost:8545'),
        'token_contract_address': os.getenv('GPUDX_TOKEN_V2_ADDRESS'),
        'escrow_contract_address': os.getenv('GPUDX_ESCROW_V2_ADDRESS'),
    }
    
    service = UtilityValidationService(config)
    
    # Example: Run continuous monitoring
    # asyncio.run(service.start_monitoring())
    
    # Instead of just running report, start FastAPI server
    import uvicorn
    from fastapi import FastAPI
    
    # Initialize utility validation service
    validation_service = UtilityValidationService(config)
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx Utility Validation Service", version="2.0.0")
    
    @app.get("/")
    async def root():
        return {"message": "GPUDx Utility Validation Service", "status": "operational"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "utility_validation"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi import Response
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
    @app.get("/utility-metrics")
    async def get_utility_metrics():
        """Get current utility metrics"""
        return await validation_service.collect_utility_metrics()
    
    @app.get("/report")
    async def get_validation_report():
        """Get utility validation report"""
        return await validation_service.get_utility_validation_report()
    
    # Start the server
    port = int(os.getenv('UTILITY_VALIDATION_PORT', '8010'))
    uvicorn.run(app, host="0.0.0.0", port=port) 