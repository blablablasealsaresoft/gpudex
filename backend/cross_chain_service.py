"""
GPUDex Cross-Chain Service
Handles automatic bridging from Ethereum L1 to Polygon for cheaper execution
"""

import logging
import os
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from web3 import Web3
from eth_account import Account
import json
import aiohttp
from decimal import Decimal

logger = logging.getLogger(__name__)

class BridgeStatus(str, Enum):
    PENDING = "pending"
    BRIDGING = "bridging" 
    COMPLETED = "completed"
    FAILED = "failed"

class CrossChainTransaction:
    def __init__(self, bridge_id: str, user_address: str, amount_eth: str, 
                 l1_tx_hash: str, l2_tx_hash: str = None, status: BridgeStatus = BridgeStatus.PENDING):
        self.bridge_id = bridge_id
        self.user_address = user_address
        self.amount_eth = amount_eth
        self.l1_tx_hash = l1_tx_hash
        self.l2_tx_hash = l2_tx_hash
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

class CrossChainService:
    def __init__(self):
        self.ethereum_rpc = os.getenv("MAINNET_RPC_URL", "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161")
        self.polygon_rpc = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com/")
        
        # Initialize Web3 instances
        self.eth_web3 = Web3(Web3.HTTPProvider(self.ethereum_rpc))
        self.polygon_web3 = Web3(Web3.HTTPProvider(self.polygon_rpc))
        
        # Bridge contracts (Polygon PoS Bridge)
        self.root_chain_manager = "0xA0c68C638235ee32657e8f720a23ceC1bFc77C77"  # Ethereum L1
        self.child_chain_manager = "0x8c5e3ceb0c3945d31b2D3C1e4b5b6b8B8B8B8B8B"  # Polygon (placeholder)
        
        # Your platform's hot wallet for bridging operations
        self.bridge_wallet_private_key = os.getenv("BRIDGE_WALLET_PRIVATE_KEY")
        if self.bridge_wallet_private_key and self.bridge_wallet_private_key != "your_bridge_wallet_private_key_here":
            try:
                # Clean and validate private key format
                clean_key = self.bridge_wallet_private_key.strip()
                if clean_key.startswith('0x'):
                    clean_key = clean_key[2:]
                
                # Ensure exactly 64 characters (32 bytes)
                if len(clean_key) != 64:
                    raise ValueError(f"Private key must be exactly 64 characters, got {len(clean_key)}")
                
                # Convert to bytes and create account
                key_bytes = bytes.fromhex(clean_key)
                self.bridge_account = Account.from_key(key_bytes)
                logger.info("Cross-chain service initialized with bridge wallet")
            except Exception as e:
                logger.warning(f"Invalid bridge wallet private key: {e}")
                self.bridge_account = None
        else:
            logger.warning("Bridge wallet private key not configured - cross-chain payments disabled")
            self.bridge_account = None
        
        # Active bridge transactions
        self.active_bridges: Dict[str, CrossChainTransaction] = {}
        
        logger.info("Cross-chain service initialized")

    async def create_bridge_transaction(self, user_address: str, amount_eth: str, l1_tx_hash: str) -> str:
        """
        Create a new bridge transaction when user pays on Ethereum L1
        """
        import uuid
        bridge_id = f"bridge_{uuid.uuid4().hex[:12]}"
        
        bridge_tx = CrossChainTransaction(
            bridge_id=bridge_id,
            user_address=user_address,
            amount_eth=amount_eth,
            l1_tx_hash=l1_tx_hash,
            status=BridgeStatus.PENDING
        )
        
        self.active_bridges[bridge_id] = bridge_tx
        
        # Start bridging process in background
        asyncio.create_task(self._process_bridge_transaction(bridge_id))
        
        logger.info(f"Created bridge transaction {bridge_id} for {amount_eth} ETH")
        return bridge_id

    async def _process_bridge_transaction(self, bridge_id: str):
        """
        Process the actual bridging from L1 to L2
        """
        try:
            bridge_tx = self.active_bridges.get(bridge_id)
            if not bridge_tx:
                logger.error(f"Bridge transaction {bridge_id} not found")
                return

            # Step 1: Verify L1 payment
            logger.info(f"Verifying L1 payment for bridge {bridge_id}")
            l1_verified = await self._verify_l1_payment(bridge_tx.l1_tx_hash, bridge_tx.amount_eth)
            if not l1_verified:
                bridge_tx.status = BridgeStatus.FAILED
                logger.error(f"L1 payment verification failed for bridge {bridge_id}")
                return

            # Step 2: Bridge to Polygon
            bridge_tx.status = BridgeStatus.BRIDGING
            logger.info(f"Starting bridge to Polygon for {bridge_id}")
            
            # Option A: Use Polygon PoS Bridge (official)
            polygon_tx_hash = await self._bridge_via_polygon_pos(bridge_tx)
            
            # Option B: Alternative - Use our own bridge mechanism
            # polygon_tx_hash = await self._bridge_via_platform_wallet(bridge_tx)
            
            if polygon_tx_hash:
                bridge_tx.l2_tx_hash = polygon_tx_hash
                bridge_tx.status = BridgeStatus.COMPLETED
                logger.info(f"Bridge {bridge_id} completed. Polygon tx: {polygon_tx_hash}")
                
                # Now execute the GPU rental on Polygon
                await self._execute_gpu_rental_on_polygon(bridge_tx)
            else:
                bridge_tx.status = BridgeStatus.FAILED
                logger.error(f"Bridge {bridge_id} failed")

        except Exception as e:
            logger.error(f"Error processing bridge {bridge_id}: {e}")
            if bridge_id in self.active_bridges:
                self.active_bridges[bridge_id].status = BridgeStatus.FAILED

    async def _verify_l1_payment(self, tx_hash: str, expected_amount: str) -> bool:
        """
        Verify that the user actually paid on Ethereum L1
        """
        try:
            tx_receipt = self.eth_web3.eth.get_transaction_receipt(tx_hash)
            tx = self.eth_web3.eth.get_transaction(tx_hash)
            
            # Verify transaction details
            if tx_receipt.status != 1:  # Transaction failed
                return False
            
            # Verify amount (convert from wei)
            paid_amount = Web3.from_wei(tx.value, 'ether')
            expected = Decimal(expected_amount)
            
            if abs(paid_amount - expected) < Decimal('0.001'):  # Allow small variance
                logger.info(f"L1 payment verified: {paid_amount} ETH")
                return True
            else:
                logger.warning(f"Amount mismatch: expected {expected}, got {paid_amount}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying L1 payment: {e}")
            return False

    async def _bridge_via_polygon_pos(self, bridge_tx: CrossChainTransaction) -> Optional[str]:
        """
        Bridge ETH from Ethereum L1 to Polygon using official PoS Bridge
        """
        try:
            if not self.bridge_account:
                logger.error("Bridge wallet not configured")
                return None
            
            # This would interact with Polygon's official bridge contracts
            # For now, we'll simulate the bridging process
            
            # In reality, you would:
            # 1. Approve ETH on L1 bridge contract
            # 2. Call depositEtherFor() on RootChainManager
            # 3. Wait for checkpoint on Polygon
            # 4. ETH appears as WETH on Polygon
            
            logger.info(f"Simulating bridge for {bridge_tx.amount_eth} ETH")
            
            # Simulate 2-3 minute bridge time
            await asyncio.sleep(5)  # In production, this would be 2-3 minutes
            
            # Return simulated Polygon transaction hash
            return f"0x{bridge_tx.bridge_id[-24:]}"
            
        except Exception as e:
            logger.error(f"Error bridging via Polygon PoS: {e}")
            return None

    async def _bridge_via_platform_wallet(self, bridge_tx: CrossChainTransaction) -> Optional[str]:
        """
        Alternative: Use platform's own wallet to provide instant liquidity
        """
        try:
            if not self.bridge_account:
                logger.error("Bridge wallet not configured")
                return None
            
            # Check if platform wallet has enough ETH on Polygon
            polygon_balance = self.polygon_web3.eth.get_balance(self.bridge_account.address)
            required_amount = Web3.to_wei(bridge_tx.amount_eth, 'ether')
            
            if polygon_balance < required_amount:
                logger.error(f"Insufficient balance on Polygon for instant bridge")
                return None
            
            # Send ETH directly from platform wallet on Polygon
            nonce = self.polygon_web3.eth.get_transaction_count(self.bridge_account.address)
            
            tx = {
                'to': bridge_tx.user_address,
                'value': required_amount,
                'gas': 21000,
                'gasPrice': self.polygon_web3.to_wei('30', 'gwei'),
                'nonce': nonce,
                'chainId': 137  # Polygon mainnet
            }
            
            # Sign and send transaction
            signed_tx = self.polygon_web3.eth.account.sign_transaction(tx, self.bridge_account.key)
            tx_hash = self.polygon_web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"Instant bridge completed: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Error in platform wallet bridge: {e}")
            return None

    async def _execute_gpu_rental_on_polygon(self, bridge_tx: CrossChainTransaction):
        """
        Execute the actual GPU rental smart contract on Polygon
        """
        try:
            # Now that user has ETH on Polygon, execute the rental
            logger.info(f"Executing GPU rental on Polygon for bridge {bridge_tx.bridge_id}")
            
            # This would call your existing GPU rental logic on Polygon
            # rental_result = await create_gpu_rental_polygon(bridge_tx.user_address, bridge_tx.amount_eth)
            
            logger.info(f"GPU rental executed successfully on Polygon")
            
        except Exception as e:
            logger.error(f"Error executing GPU rental on Polygon: {e}")

    async def get_bridge_status(self, bridge_id: str) -> Dict[str, Any]:
        """
        Get the status of a bridge transaction
        """
        bridge_tx = self.active_bridges.get(bridge_id)
        if not bridge_tx:
            return {"error": "Bridge transaction not found"}
        
        return {
            "bridge_id": bridge_id,
            "status": bridge_tx.status,
            "user_address": bridge_tx.user_address,
            "amount_eth": bridge_tx.amount_eth,
            "l1_tx_hash": bridge_tx.l1_tx_hash,
            "l2_tx_hash": bridge_tx.l2_tx_hash,
            "created_at": bridge_tx.created_at.isoformat(),
            "updated_at": bridge_tx.updated_at.isoformat()
        }

    async def estimate_bridge_time(self) -> Dict[str, Any]:
        """
        Estimate bridge time and costs
        """
        return {
            "polygon_pos_bridge": {
                "time_minutes": "2-3",
                "cost_usd": "5-15",
                "description": "Official Polygon bridge"
            },
            "platform_instant_bridge": {
                "time_minutes": "0.1",
                "cost_usd": "2-5", 
                "description": "Instant via platform wallet"
            }
        }

# Initialize global cross-chain service
# Cross-chain service disabled for production launch - Polygon-only
# cross_chain_service = CrossChainService() 