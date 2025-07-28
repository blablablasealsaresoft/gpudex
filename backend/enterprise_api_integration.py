#!/usr/bin/env python3
"""
GPUDex Enterprise API Integration Layer
Connecting frontend portal to backend services and smart contracts
BILL GATES ON ADDERALL: MAXIMUM API VELOCITY!
"""

import asyncio
import json
import logging
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from functools import wraps
import sqlite3
import aiohttp
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError
from fastapi import FastAPI, HTTPException, Depends, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class EnterpriseRegistrationRequest(BaseModel):
    company_name: str
    contact_email: str
    tier: int  # 0-4 (Startup to Platinum)
    contract_type: int  # 0-4 (Pay-per-use to Custom)
    wallet_address: str

class InstitutionalStakingRequest(BaseModel):
    institution_name: str
    stake_amount: float
    custom_apy: float
    lock_period_days: int
    wallet_address: str

class PricingQuoteRequest(BaseModel):
    gpu_type: str
    hours_needed: int
    client_address: str

class RevenueAnalyticsResponse(BaseModel):
    total_revenue: float
    active_clients: int
    growth_rate: float
    monthly_recurring_revenue: float
    tier_distribution: Dict[str, int]
    revenue_trends: List[Dict[str, Any]]

class ClientProfileResponse(BaseModel):
    client_address: str
    company_name: str
    tier: str
    total_spent: float
    gpu_hours: int
    discount_rate: float
    tier_progress: float
    next_tier_requirement: float

class TransactionResponse(BaseModel):
    transaction_hash: str
    status: str
    block_number: Optional[int]
    gas_used: Optional[int]
    timestamp: float

# API Integration Service
class EnterpriseAPIIntegration:
    """Comprehensive API integration layer for enterprise services"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_path = config.get('database_path', 'enterprise_api.db')
        self.web3 = Web3(Web3.HTTPProvider(config['rpc_url']))
        self.app = FastAPI(title="GPUDex Enterprise API", version="2.0.0")
        
        # Smart contracts
        self.enterprise_contract = None
        self.token_contract = None
        self.advanced_tokenomics_contract = None
        
        # Authentication
        self.security = HTTPBearer()
        self.api_keys = config.get('api_keys', {})
        
        # Initialize
        self._init_database()
        self._load_contracts()
        self._setup_middleware()
        self._setup_routes()
    
    def _init_database(self):
        """Initialize API database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # API sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_sessions (
                session_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                api_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # API call logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                wallet_address TEXT,
                request_data TEXT,
                response_status INTEGER,
                response_time REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Transaction queue table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_hash TEXT UNIQUE,
                wallet_address TEXT NOT NULL,
                contract_address TEXT NOT NULL,
                function_name TEXT NOT NULL,
                parameters TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("API integration database initialized")
    
    def _load_contracts(self):
        """Load smart contracts"""
        try:
            # Load contract ABIs (simplified for demo)
            enterprise_abi = []
            token_abi = []
            advanced_tokenomics_abi = []
            
            self.enterprise_contract = self.web3.eth.contract(
                address=self.config['enterprise_contract_address'],
                abi=enterprise_abi
            )
            
            self.token_contract = self.web3.eth.contract(
                address=self.config['token_contract_address'],
                abi=token_abi
            )
            
            self.advanced_tokenomics_contract = self.web3.eth.contract(
                address=self.config['advanced_tokenomics_address'],
                abi=advanced_tokenomics_abi
            )
            
            logger.info("Smart contracts loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load contracts: {e}")
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log API call
            await self._log_api_call(
                endpoint=str(request.url.path),
                method=request.method,
                wallet_address=getattr(request.state, 'wallet_address', None),
                request_data=None,  # Could capture request body
                response_status=response.status_code,
                response_time=process_time
            )
            
            return response
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "GPUDex Enterprise API",
                "version": "2.0.0",
                "status": "active",
                "endpoints": {
                    "enterprise": "/api/v2/enterprise/",
                    "analytics": "/api/v2/analytics/",
                    "pricing": "/api/v2/pricing/",
                    "institutional": "/api/v2/institutional/",
                    "transactions": "/api/v2/transactions/"
                }
            }
        
        # Enterprise client endpoints
        @self.app.post("/api/v2/enterprise/register")
        async def register_enterprise_client(
            request: EnterpriseRegistrationRequest,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._register_enterprise_client(request, wallet_auth)
        
        @self.app.get("/api/v2/enterprise/profile/{wallet_address}")
        async def get_client_profile(
            wallet_address: str,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._get_client_profile(wallet_address, wallet_auth)
        
        @self.app.get("/api/v2/enterprise/tier-info/{wallet_address}")
        async def get_tier_info(
            wallet_address: str,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._get_tier_info(wallet_address)
        
        # Analytics endpoints
        @self.app.get("/api/v2/analytics/revenue")
        async def get_revenue_analytics(
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._get_revenue_analytics()
        
        @self.app.get("/api/v2/analytics/client/{wallet_address}")
        async def get_client_analytics(
            wallet_address: str,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._get_client_analytics(wallet_address)
        
        # Pricing endpoints
        @self.app.post("/api/v2/pricing/quote")
        async def get_pricing_quote(
            request: PricingQuoteRequest,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._get_pricing_quote(request)
        
        @self.app.get("/api/v2/pricing/tiers")
        async def get_pricing_tiers():
            return await self._get_pricing_tiers()
        
        # Institutional staking endpoints
        @self.app.post("/api/v2/institutional/apply")
        async def apply_institutional_staking(
            request: InstitutionalStakingRequest,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._apply_institutional_staking(request, wallet_auth)
        
        @self.app.get("/api/v2/institutional/programs")
        async def get_institutional_programs():
            return await self._get_institutional_programs()
        
        # Transaction endpoints
        @self.app.get("/api/v2/transactions/{tx_hash}")
        async def get_transaction_status(
            tx_hash: str,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._get_transaction_status(tx_hash)
        
        @self.app.get("/api/v2/transactions/history/{wallet_address}")
        async def get_transaction_history(
            wallet_address: str,
            limit: int = 10,
            wallet_auth = Depends(self._verify_wallet_signature)
        ):
            return await self._get_transaction_history(wallet_address, limit)
        
        # Advanced tokenomics endpoints
        @self.app.get("/api/v2/tokenomics/apy")
        async def get_current_apy():
            return await self._get_current_apy()
        
        @self.app.get("/api/v2/tokenomics/burn-stats")
        async def get_burn_statistics():
            return await self._get_burn_statistics()
        
        @self.app.get("/api/v2/tokenomics/cross-chain")
        async def get_cross_chain_info():
            return await self._get_cross_chain_info()
    
    # Authentication methods
    async def _verify_wallet_signature(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        """Verify wallet signature or API key"""
        try:
            token = credentials.credentials
            
            # Check if it's an API key
            if token in self.api_keys.values():
                return {"authenticated": True, "method": "api_key"}
            
            # For demo, we'll simulate wallet signature verification
            # In production, verify the signature against the message
            return {"authenticated": True, "method": "wallet_signature", "wallet": "0x..."}
            
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid authentication")
    
    # Enterprise client methods
    async def _register_enterprise_client(self, request: EnterpriseRegistrationRequest, auth):
        """Register new enterprise client"""
        try:
            # Validate request
            if not self.web3.is_address(request.wallet_address):
                raise HTTPException(status_code=400, detail="Invalid wallet address")
            
            # Call smart contract
            # tx_hash = await self._execute_contract_function(
            #     self.enterprise_contract.functions.registerEnterpriseClient(
            #         request.company_name,
            #         request.contact_email,
            #         request.tier,
            #         request.contract_type
            #     ),
            #     request.wallet_address
            # )
            
            # Simulate successful registration
            tx_hash = "0x" + "1" * 64
            
            # Queue transaction for monitoring
            await self._queue_transaction(
                tx_hash,
                request.wallet_address,
                self.config['enterprise_contract_address'],
                "registerEnterpriseClient",
                json.dumps(asdict(request))
            )
            
            return TransactionResponse(
                transaction_hash=tx_hash,
                status="pending",
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Enterprise registration error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_client_profile(self, wallet_address: str, auth):
        """Get client profile information"""
        try:
            # Get data from smart contract
            # client_data = self.enterprise_contract.functions.getEnterpriseClient(wallet_address).call()
            
            # Simulate client data
            mock_profile = ClientProfileResponse(
                client_address=wallet_address,
                company_name="AI Startup Co",
                tier="Professional",
                total_spent=45750.0,
                gpu_hours=915,
                discount_rate=15.0,
                tier_progress=75.0,
                next_tier_requirement=100000.0
            )
            
            return mock_profile
            
        except Exception as e:
            logger.error(f"Get client profile error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_tier_info(self, wallet_address: str):
        """Get client tier information and upgrade requirements"""
        try:
            # Get tier configuration from smart contract
            tiers = {
                "STARTUP": {"minimum": 1000, "discount": 5},
                "GROWTH": {"minimum": 5000, "discount": 10},
                "PROFESSIONAL": {"minimum": 25000, "discount": 15},
                "ENTERPRISE": {"minimum": 100000, "discount": 20},
                "PLATINUM": {"minimum": 500000, "discount": 30}
            }
            
            return {
                "current_tier": "PROFESSIONAL",
                "current_spending": 45750,
                "tier_requirements": tiers,
                "next_tier": "ENTERPRISE",
                "amount_to_next_tier": 54250,
                "tier_benefits": {
                    "ENTERPRISE": [
                        "20% discount on all GPU rentals",
                        "Priority GPU access",
                        "Custom pricing options",
                        "Dedicated account manager"
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Get tier info error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Analytics methods
    async def _get_revenue_analytics(self):
        """Get comprehensive revenue analytics"""
        try:
            # Get platform metrics from smart contract
            # metrics = self.enterprise_contract.functions.getEnterpriseMetrics().call()
            
            # Simulate analytics data
            analytics = RevenueAnalyticsResponse(
                total_revenue=2450000.0,
                active_clients=156,
                growth_rate=34.5,
                monthly_recurring_revenue=425000.0,
                tier_distribution={
                    "STARTUP": 45,
                    "GROWTH": 38,
                    "PROFESSIONAL": 32,
                    "ENTERPRISE": 28,
                    "PLATINUM": 13
                },
                revenue_trends=[
                    {"month": "2024-01", "revenue": 380000},
                    {"month": "2024-02", "revenue": 420000},
                    {"month": "2024-03", "revenue": 465000},
                    {"month": "2024-04", "revenue": 510000},
                    {"month": "2024-05", "revenue": 425000}
                ]
            )
            
            return analytics
            
        except Exception as e:
            logger.error(f"Get revenue analytics error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_client_analytics(self, wallet_address: str):
        """Get specific client analytics"""
        try:
            # Simulate client-specific analytics
            return {
                "client_address": wallet_address,
                "usage_analytics": {
                    "total_gpu_hours": 915,
                    "average_session_length": 4.2,
                    "most_used_gpu": "NVIDIA A100",
                    "total_savings": 6862.50
                },
                "spending_analytics": {
                    "total_spent": 45750,
                    "monthly_average": 7625,
                    "spending_trend": "increasing",
                    "cost_per_hour": 50.0
                },
                "performance_metrics": {
                    "utilization_rate": 87.3,
                    "efficiency_score": 94.2,
                    "satisfaction_rating": 4.8
                }
            }
            
        except Exception as e:
            logger.error(f"Get client analytics error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Pricing methods
    async def _get_pricing_quote(self, request: PricingQuoteRequest):
        """Generate pricing quote for client"""
        try:
            # Base GPU prices
            gpu_prices = {
                "h100": 4.00,
                "a100": 2.50,
                "v100": 1.50,
                "rtx4090": 0.80
            }
            
            base_price = gpu_prices.get(request.gpu_type, 2.50)
            base_cost = base_price * request.hours_needed
            
            # Get client tier discount
            # client_info = self.enterprise_contract.functions.getEnterpriseClient(request.client_address).call()
            discount_rate = 0.15  # 15% for Professional tier
            
            discount_amount = base_cost * discount_rate
            final_cost = base_cost - discount_amount
            
            return {
                "gpu_type": request.gpu_type,
                "hours_requested": request.hours_needed,
                "base_price_per_hour": base_price,
                "base_cost": base_cost,
                "discount_rate": discount_rate,
                "discount_amount": discount_amount,
                "final_cost": final_cost,
                "estimated_completion": "2-4 hours",
                "quote_valid_until": (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Get pricing quote error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_pricing_tiers(self):
        """Get all pricing tiers and their benefits"""
        return {
            "tiers": {
                "STARTUP": {
                    "minimum_monthly": 1000,
                    "discount_rate": 0.05,
                    "benefits": ["Basic support", "Standard GPU access", "Monthly billing"]
                },
                "GROWTH": {
                    "minimum_monthly": 5000,
                    "discount_rate": 0.10,
                    "benefits": ["Priority support", "Extended GPU access", "Quarterly billing"]
                },
                "PROFESSIONAL": {
                    "minimum_monthly": 25000,
                    "discount_rate": 0.15,
                    "benefits": ["Premium support", "Priority GPU access", "Custom billing", "Analytics dashboard"]
                },
                "ENTERPRISE": {
                    "minimum_monthly": 100000,
                    "discount_rate": 0.20,
                    "benefits": ["Dedicated account manager", "Custom pricing", "SLA guarantees", "White-label options"]
                },
                "PLATINUM": {
                    "minimum_monthly": 500000,
                    "discount_rate": 0.30,
                    "benefits": ["Executive support", "Custom infrastructure", "Revenue sharing", "Partnership opportunities"]
                }
            },
            "upgrade_requirements": {
                "automatic_upgrade": True,
                "based_on": "total_spending",
                "evaluation_period": "monthly"
            }
        }
    
    # Institutional staking methods
    async def _apply_institutional_staking(self, request: InstitutionalStakingRequest, auth):
        """Apply for institutional staking program"""
        try:
            # Validate minimum requirements
            if request.stake_amount < 1000000:  # 1M GPUDX minimum
                raise HTTPException(status_code=400, detail="Minimum stake of 1M GPUDX required")
            
            if request.lock_period_days < 30:
                raise HTTPException(status_code=400, detail="Minimum lock period of 30 days required")
            
            # Call smart contract to create institutional program
            # tx_hash = await self._execute_contract_function(
            #     self.advanced_tokenomics_contract.functions.createInstitutionalStaking(
            #         request.wallet_address,
            #         request.institution_name,
            #         int(request.custom_apy * 100),  # Convert to basis points
            #         request.lock_period_days,
            #         int(request.stake_amount * 10**18)  # Convert to wei
            #     ),
            #     request.wallet_address
            # )
            
            # Simulate transaction
            tx_hash = "0x" + "2" * 64
            
            return TransactionResponse(
                transaction_hash=tx_hash,
                status="pending",
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Institutional staking application error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_institutional_programs(self):
        """Get available institutional staking programs"""
        return {
            "standard_program": {
                "minimum_stake": 1000000,
                "base_apy": 0.15,
                "lock_period_days": 365,
                "benefits": ["Priority GPU access", "Custom APY rates", "Dedicated support"]
            },
            "custom_programs": [
                {
                    "name": "AI Research Institutions",
                    "minimum_stake": 5000000,
                    "custom_apy": 0.25,
                    "lock_period_days": 730,
                    "special_benefits": ["Research grants", "Early GPU access", "Co-development opportunities"]
                },
                {
                    "name": "Enterprise Partnerships",
                    "minimum_stake": 10000000,
                    "custom_apy": 0.35,
                    "lock_period_days": 1095,
                    "special_benefits": ["Revenue sharing", "White-label licensing", "Strategic partnership"]
                }
            ],
            "application_process": {
                "steps": ["Submit application", "Due diligence review", "Terms negotiation", "Contract execution"],
                "timeline": "2-4 weeks",
                "requirements": ["Institutional verification", "Compliance documentation", "Stake commitment"]
            }
        }
    
    # Transaction methods
    async def _get_transaction_status(self, tx_hash: str):
        """Get transaction status and details"""
        try:
            # Check blockchain for transaction
            try:
                tx_receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                return TransactionResponse(
                    transaction_hash=tx_hash,
                    status="confirmed" if tx_receipt.status == 1 else "failed",
                    block_number=tx_receipt.blockNumber,
                    gas_used=tx_receipt.gasUsed,
                    timestamp=time.time()
                )
            except:
                # Check pending transactions
                return TransactionResponse(
                    transaction_hash=tx_hash,
                    status="pending",
                    timestamp=time.time()
                )
                
        except Exception as e:
            logger.error(f"Get transaction status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_transaction_history(self, wallet_address: str, limit: int):
        """Get transaction history for wallet"""
        try:
            # Simulate transaction history
            history = []
            for i in range(min(limit, 10)):
                history.append({
                    "transaction_hash": f"0x{'1' * 64}",
                    "type": "enterprise_registration" if i % 3 == 0 else "gpu_rental",
                    "amount": 1500.0 + (i * 200),
                    "status": "confirmed",
                    "timestamp": time.time() - (i * 24 * 60 * 60),
                    "block_number": 12345678 + i
                })
            
            return {
                "wallet_address": wallet_address,
                "transaction_count": len(history),
                "transactions": history
            }
            
        except Exception as e:
            logger.error(f"Get transaction history error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Advanced tokenomics methods
    async def _get_current_apy(self):
        """Get current dynamic APY"""
        try:
            # Get APY from smart contract
            # current_apy = self.advanced_tokenomics_contract.functions.getCurrentAPY().call()
            
            return {
                "current_apy": 0.125,  # 12.5%
                "base_apy": 0.10,
                "demand_multiplier": 1.25,
                "last_updated": time.time() - 3600,
                "next_update": time.time() + 3600,
                "apy_range": {"min": 0.05, "max": 0.50}
            }
            
        except Exception as e:
            logger.error(f"Get current APY error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_burn_statistics(self):
        """Get token burn statistics"""
        try:
            # Get burn stats from smart contract
            # burn_stats = self.advanced_tokenomics_contract.functions.getBurnStatistics().call()
            
            return {
                "total_burned": 1250000,
                "burn_rate": 0.015,  # 1.5%
                "deflation_rate": 0.02,  # 2%
                "last_burn_amount": 50000,
                "last_burn_time": time.time() - (24 * 60 * 60),
                "next_burn_estimate": time.time() + (24 * 60 * 60),
                "burn_reasons": {
                    "demand_based": 0.60,
                    "revenue_based": 0.25,
                    "bridge_fees": 0.15
                }
            }
            
        except Exception as e:
            logger.error(f"Get burn statistics error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _get_cross_chain_info(self):
        """Get cross-chain bridge information"""
        try:
            return {
                "supported_chains": [
                    {"chain_id": 1, "name": "Ethereum", "bridge_fee": 0.005, "active": True},
                    {"chain_id": 56, "name": "BSC", "bridge_fee": 0.002, "active": True},
                    {"chain_id": 42161, "name": "Arbitrum", "bridge_fee": 0.001, "active": True},
                    {"chain_id": 10, "name": "Optimism", "bridge_fee": 0.001, "active": False}
                ],
                "total_bridged": 5250000,
                "bridge_statistics": {
                    "total_transactions": 1847,
                    "total_volume": 12500000,
                    "average_bridge_amount": 6771
                }
            }
            
        except Exception as e:
            logger.error(f"Get cross-chain info error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Utility methods
    async def _execute_contract_function(self, contract_function, from_address: str):
        """Execute smart contract function"""
        try:
            # Build transaction
            transaction = contract_function.buildTransaction({
                'from': from_address,
                'gas': 500000,
                'gasPrice': self.web3.toWei('30', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(from_address)
            })
            
            # In production, this would be signed by the user's wallet
            # For now, we'll simulate the transaction hash
            tx_hash = "0x" + hashlib.sha256(json.dumps(transaction).encode()).hexdigest()
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"Contract execution error: {e}")
            raise
    
    async def _queue_transaction(self, tx_hash: str, wallet_address: str, contract_address: str, function_name: str, parameters: str):
        """Queue transaction for monitoring"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO transaction_queue 
                (transaction_hash, wallet_address, contract_address, function_name, parameters)
                VALUES (?, ?, ?, ?, ?)
            ''', (tx_hash, wallet_address, contract_address, function_name, parameters))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Queue transaction error: {e}")
    
    async def _log_api_call(self, endpoint: str, method: str, wallet_address: Optional[str], request_data: Optional[str], response_status: int, response_time: float):
        """Log API call for analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO api_logs 
                (endpoint, method, wallet_address, request_data, response_status, response_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (endpoint, method, wallet_address, request_data, response_status, response_time))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Log API call error: {e}")
    
    def start_api_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the API server"""
        logger.info(f"🚀 Starting GPUDex Enterprise API on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

# Example usage and configuration
if __name__ == "__main__":
    import os
    config = {
        'database_path': 'enterprise_api.db',
        'rpc_url': os.getenv('RPC_URL', 'http://localhost:8545'),
        'enterprise_contract_address': os.getenv('GPUDX_ENTERPRISE_V2_ADDRESS', '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0'),
        'token_contract_address': os.getenv('GPUDX_TOKEN_V2_ADDRESS', '0x5FbDB2315678afecb367f032d93F642f64180aa3'),
        'advanced_tokenomics_address': os.getenv('GPUDX_ADVANCED_TOKENOMICS_V2_ADDRESS', '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9'),
        'api_keys': {
            'admin': 'gpudx_admin_key_2024',
            'enterprise': 'gpudx_enterprise_key_2024'
        }
    }
    
    # Initialize and start API service
    api_service = EnterpriseAPIIntegration(config)
    api_service.start_api_server(host="0.0.0.0", port=8000) 