"""
GPUDex Token Service - $GPUDX Integration
Handles token payments, staking, and rewards (SIMPLIFIED - NO GOVERNANCE)
"""

import os
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
from web3 import Web3
from eth_account import Account
import json
from dataclasses import dataclass
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()

@dataclass
class TokenReward:
    user_address: str
    amount: Decimal
    reward_type: str  # 'staking', 'referral', 'provider', 'loyalty'
    timestamp: datetime
    transaction_hash: str

@dataclass
class StakingPosition:
    user_address: str
    amount: Decimal
    stake_date: datetime
    unlock_date: datetime
    apy_rate: float
    tier: str  # 'bronze', 'silver', 'gold', 'diamond'

class TokenBalance(Base):
    __tablename__ = "token_balances"
    
    id = Column(Integer, primary_key=True)
    user_address = Column(String(42), index=True, nullable=False)
    balance = Column(Float, default=0.0)
    staked_amount = Column(Float, default=0.0)
    rewards_earned = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
class StakingRecord(Base):
    __tablename__ = "staking_records"
    
    id = Column(Integer, primary_key=True)
    user_address = Column(String(42), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    apy_rate = Column(Float, nullable=False)
    tier = Column(String(20), nullable=False)
    stake_date = Column(DateTime, default=datetime.utcnow)
    unlock_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    rewards_claimed = Column(Float, default=0.0)

class TokenPayment(Base):
    __tablename__ = "token_payments"
    
    id = Column(Integer, primary_key=True)
    from_address = Column(String(42), index=True, nullable=False)
    to_address = Column(String(42), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(String(50), nullable=False)  # 'gpu_rental', 'platform_fee', 'reward'
    transaction_hash = Column(String(66), unique=True)
    block_number = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='pending')  # 'pending', 'confirmed', 'failed'

class GPUDXTokenService:
    def __init__(self):
        self.web3 = self._initialize_web3()
        self.contract = self._load_token_contract()
        self.db = self._initialize_database()
        
        # Simplified token economics - NO GOVERNANCE
        self.staking_tiers = {
            'bronze': {'min_amount': 1000, 'apy': 0.08, 'perks': ['Basic support', 'Standard fees']},
            'silver': {'min_amount': 10000, 'apy': 0.12, 'perks': ['Priority support', '2% fee discount']},
            'gold': {'min_amount': 100000, 'apy': 0.15, 'perks': ['Premium support', '5% fee discount', 'Early access']},
            'diamond': {'min_amount': 1000000, 'apy': 0.20, 'perks': ['VIP support', '10% fee discount', 'Beta features', 'Revenue sharing']}
        }
        
        # Payment discounts for $GPUDX usage
        self.token_discount_rate = 0.05  # 5% discount
        
        logger.info("GPUDXTokenService initialized (Governance-free)")
    
    def _initialize_web3(self) -> Web3:
        """Initialize Web3 connection to Polygon"""
        rpc_url = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com/')
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not w3.is_connected():
            raise Exception("Failed to connect to Polygon network")
        
        return w3
    
    def _load_token_contract(self):
        """Load the $GPUDX token contract"""
        token_address = os.getenv('TOKEN_CONTRACT_ADDRESS', '0x386FF386B396ca139E5D2dB6d0b61a0FDd5b4b47')
        
        # ERC20 ABI (basic functions)
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        return self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=erc20_abi
        )
    
    def _initialize_database(self):
        """Initialize database connection"""
        database_url = os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        engine = create_engine(database_url)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    async def get_token_balance(self, user_address: str) -> Dict[str, float]:
        """Get user's $GPUDX token balance"""
        try:
            # Get on-chain balance
            balance_wei = self.contract.functions.balanceOf(
                Web3.to_checksum_address(user_address)
            ).call()
            balance = Web3.from_wei(balance_wei, 'ether')
            
            # Get staking info from database
            db_balance = self.db.query(TokenBalance).filter(
                TokenBalance.user_address == user_address
            ).first()
            
            if not db_balance:
                db_balance = TokenBalance(
                    user_address=user_address,
                    balance=float(balance),
                    staked_amount=0.0,
                    rewards_earned=0.0
                )
                self.db.add(db_balance)
                self.db.commit()
            
            tier = self._get_staking_tier(db_balance.staked_amount)
            
            return {
                'total_balance': float(balance),
                'available_balance': float(balance) - db_balance.staked_amount,
                'staked_amount': db_balance.staked_amount,
                'rewards_earned': db_balance.rewards_earned,
                'staking_tier': tier,
                'tier_perks': self.staking_tiers.get(tier, {}).get('perks', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return {'total_balance': 0.0, 'available_balance': 0.0, 'staked_amount': 0.0, 'rewards_earned': 0.0}
    
    def _get_staking_tier(self, staked_amount: float) -> str:
        """Determine staking tier based on amount"""
        for tier in ['diamond', 'gold', 'silver', 'bronze']:
            if staked_amount >= self.staking_tiers[tier]['min_amount']:
                return tier
        return 'none'
    
    async def stake_tokens(self, user_address: str, amount: float, lock_period_days: int = 30) -> Dict[str, Any]:
        """Stake $GPUDX tokens for rewards"""
        try:
            tier = self._get_staking_tier(amount)
            if tier == 'none':
                return {'success': False, 'error': 'Minimum staking amount not met (1000 GPUDX)'}
            
            apy_rate = self.staking_tiers[tier]['apy']
            unlock_date = datetime.utcnow() + timedelta(days=lock_period_days)
            
            # Create staking record
            staking_record = StakingRecord(
                user_address=user_address,
                amount=amount,
                apy_rate=apy_rate,
                tier=tier,
                unlock_date=unlock_date
            )
            self.db.add(staking_record)
            
            # Update user balance
            user_balance = self.db.query(TokenBalance).filter(
                TokenBalance.user_address == user_address
            ).first()
            
            if user_balance:
                user_balance.staked_amount += amount
            else:
                user_balance = TokenBalance(
                    user_address=user_address,
                    staked_amount=amount
                )
                self.db.add(user_balance)
            
            self.db.commit()
            
            return {
                'success': True,
                'staking_id': staking_record.id,
                'tier': tier,
                'apy_rate': apy_rate,
                'unlock_date': unlock_date.isoformat(),
                'estimated_rewards': amount * apy_rate * (lock_period_days / 365),
                'tier_perks': self.staking_tiers[tier]['perks']
            }
            
        except Exception as e:
            logger.error(f"Error staking tokens: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def calculate_gpu_payment(self, hours: float, hourly_rate: float, use_token: bool = False, user_tier: str = 'none') -> Dict[str, Any]:
        """Calculate payment for GPU rental with token discount and tier benefits"""
        base_cost = hours * hourly_rate
        
        if use_token:
            # Base 5% discount for $GPUDX payments
            discount_rate = self.token_discount_rate
            
            # Additional tier-based discounts
            tier_discounts = {
                'silver': 0.02,  # +2% 
                'gold': 0.05,    # +5%
                'diamond': 0.10  # +10%
            }
            
            if user_tier in tier_discounts:
                discount_rate += tier_discounts[user_tier]
            
            discounted_cost = base_cost * (1 - discount_rate)
            token_amount = discounted_cost  # 1:1 USD to GPUDX for now
            
            return {
                'base_cost_usd': base_cost,
                'discount_percent': discount_rate * 100,
                'discount_amount': base_cost - discounted_cost,
                'final_cost_gpudx': token_amount,
                'savings': base_cost - discounted_cost,
                'tier_bonus': tier_discounts.get(user_tier, 0) * 100
            }
        else:
            return {
                'base_cost_usd': base_cost,
                'final_cost_usd': base_cost,
                'potential_savings': base_cost * self.token_discount_rate,
                'upgrade_to_save': 'Stake 1000+ GPUDX for 5-15% discounts'
            }
    
    async def process_gpu_payment(self, from_address: str, to_address: str, amount: float, gpu_rental_id: str) -> Dict[str, Any]:
        """Process $GPUDX payment for GPU rental"""
        try:
            # Calculate platform fee (3%)
            platform_fee = amount * 0.03
            provider_amount = amount - platform_fee
            
            # Record payment
            payment = TokenPayment(
                from_address=from_address,
                to_address=to_address,
                amount=amount,
                payment_type='gpu_rental',
                status='confirmed'  # Simplified for now - would need actual blockchain verification
            )
            self.db.add(payment)
            
            # Award provider earnings
            await self._award_provider_tokens(to_address, provider_amount)
            
            self.db.commit()
            
            return {
                'success': True,
                'payment_id': payment.id,
                'total_amount': amount,
                'platform_fee': platform_fee,
                'provider_earnings': provider_amount,
                'transaction_hash': 'simulated_hash_' + str(payment.id)  # Would be real tx hash
            }
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def _award_provider_tokens(self, provider_address: str, amount: float):
        """Award tokens to GPU provider"""
        # Update provider balance
        provider_balance = self.db.query(TokenBalance).filter(
            TokenBalance.user_address == provider_address
        ).first()
        
        if provider_balance:
            provider_balance.balance += amount
        else:
            provider_balance = TokenBalance(
                user_address=provider_address,
                balance=amount
            )
            self.db.add(provider_balance)
    
    async def get_staking_rewards(self, user_address: str) -> Dict[str, Any]:
        """Calculate available staking rewards"""
        try:
            active_stakes = self.db.query(StakingRecord).filter(
                StakingRecord.user_address == user_address,
                StakingRecord.is_active == True
            ).all()
            
            total_rewards = 0.0
            stake_details = []
            
            for stake in active_stakes:
                # Calculate rewards based on time elapsed
                days_staked = (datetime.utcnow() - stake.stake_date).days
                daily_reward = (stake.amount * stake.apy_rate) / 365
                earned_rewards = days_staked * daily_reward - stake.rewards_claimed
                
                total_rewards += earned_rewards
                
                stake_details.append({
                    'stake_id': stake.id,
                    'amount': stake.amount,
                    'apy_rate': stake.apy_rate,
                    'tier': stake.tier,
                    'days_staked': days_staked,
                    'earned_rewards': earned_rewards,
                    'unlock_date': stake.unlock_date.isoformat(),
                    'can_unstake': datetime.utcnow() >= stake.unlock_date
                })
            
            return {
                'total_rewards': total_rewards,
                'stakes': stake_details,
                'can_claim': total_rewards > 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating staking rewards: {e}")
            return {'total_rewards': 0.0, 'stakes': [], 'can_claim': False}

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    # Configuration
    config = {
        'database_url': os.getenv('DATABASE_URL', 'postgresql://gpudex:password@postgres:5432/gpudex_db'),
        'rpc_url': os.getenv('RPC_URL', 'https://polygon-rpc.com'),
        'token_contract_address': os.getenv('GPUDX_TOKEN_V2_ADDRESS', '0x5FbDB2315678afecb367f032d93F642f64180aa3'),
        'private_key': os.getenv('DEPLOYER_PRIVATE_KEY', ''),
        'port': int(os.getenv('TOKEN_SERVICE_PORT', '8004'))
    }
    
    # Initialize token service
    token_service = GPUDXTokenService()
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx Token Service", version="2.0.0")
    
    # Add CORS middleware
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:80", "http://127.0.0.1", "http://127.0.0.1:80"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {"message": "GPUDx Token Service", "status": "operational"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "token_service"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from fastapi import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return {"error": "Prometheus client not available", "service": "token_service"}
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=config['port']) 