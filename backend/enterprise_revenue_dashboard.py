#!/usr/bin/env python3
"""
GPUDex Enterprise Revenue Dashboard
Real-time B2B analytics, client management, and revenue optimization
BILL GATES ON ADDERALL: MAXIMUM REVENUE TRACKING!
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
from enum import Enum
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
except ImportError:
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnterpriseTier(Enum):
    STARTUP = 0
    GROWTH = 1 
    PROFESSIONAL = 2
    ENTERPRISE = 3
    PLATINUM = 4

class ContractType(Enum):
    PAYPERUSE = 0
    MONTHLY = 1
    QUARTERLY = 2
    ANNUAL = 3
    CUSTOM = 4

@dataclass
class EnterpriseClient:
    """Enterprise client data structure"""
    client_address: str
    company_name: str
    contact_email: str
    tier: EnterpriseTier
    contract_type: ContractType
    volume_discount: float
    monthly_commitment: float
    total_spent: float
    total_hours: int
    joined_at: float
    is_active: bool
    has_custom_pricing: bool
    custom_price_per_hour: float

@dataclass
class RevenueMetrics:
    """Revenue analytics data structure"""
    timestamp: float
    total_enterprise_revenue: float
    active_enterprise_clients: int
    average_revenue_per_client: float
    monthly_recurring_revenue: float
    annual_contract_value: float
    client_acquisition_cost: float
    client_lifetime_value: float
    churn_rate: float
    growth_rate: float

@dataclass
class ClientPerformance:
    """Individual client performance metrics"""
    client_address: str
    company_name: str
    tier: str
    total_revenue: float
    monthly_average: float
    gpu_hours_used: int
    discount_savings: float
    payment_history: List[Dict]
    usage_trends: Dict[str, float]
    satisfaction_score: float

class EnterpriseRevenueDashboard:
    """Service for enterprise revenue tracking and analytics"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_path = config.get('database_path', 'enterprise_revenue.db')
        self.web3 = Web3(Web3.HTTPProvider(config['rpc_url']))
        self.enterprise_contract = None
        self.revenue_history = []
        
        # Initialize database
        self._init_database()
        
        # Load contract
        self._load_enterprise_contract()
    
    def _init_database(self):
        """Initialize SQLite database for enterprise revenue tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enterprise clients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enterprise_clients (
                client_address TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                contact_email TEXT,
                tier INTEGER NOT NULL,
                contract_type INTEGER NOT NULL,
                volume_discount REAL DEFAULT 0,
                monthly_commitment REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                total_hours INTEGER DEFAULT 0,
                joined_at REAL NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                has_custom_pricing BOOLEAN DEFAULT FALSE,
                custom_price_per_hour REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Revenue transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_address TEXT NOT NULL,
                transaction_hash TEXT,
                amount REAL NOT NULL,
                discount_applied REAL DEFAULT 0,
                gpu_hours INTEGER NOT NULL,
                gpu_type TEXT,
                timestamp REAL NOT NULL,
                block_number INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_address) REFERENCES enterprise_clients(client_address)
            )
        ''')
        
        # Revenue metrics history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                total_enterprise_revenue REAL NOT NULL,
                active_enterprise_clients INTEGER NOT NULL,
                average_revenue_per_client REAL NOT NULL,
                monthly_recurring_revenue REAL NOT NULL,
                annual_contract_value REAL NOT NULL,
                growth_rate REAL NOT NULL,
                churn_rate REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Client tier upgrades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tier_upgrades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_address TEXT NOT NULL,
                old_tier INTEGER NOT NULL,
                new_tier INTEGER NOT NULL,
                upgrade_reason TEXT,
                timestamp REAL NOT NULL,
                revenue_at_upgrade REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_address) REFERENCES enterprise_clients(client_address)
            )
        ''')
        
        # Institutional staking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS institutional_staking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                institution_address TEXT NOT NULL,
                institution_name TEXT NOT NULL,
                staked_amount REAL NOT NULL,
                custom_apy REAL NOT NULL,
                lock_period_days INTEGER NOT NULL,
                staked_at REAL NOT NULL,
                locked_until REAL NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Enterprise revenue database initialized successfully")
    
    def _load_enterprise_contract(self):
        """Load enterprise smart contract"""
        try:
            # Load contract ABI (would be loaded from file in production)
            enterprise_abi = []  # Load from artifacts/contracts/GPUDexEnterpriseV2.sol/GPUDexEnterpriseV2.json
            
            self.enterprise_contract = self.web3.eth.contract(
                address=self.config['enterprise_contract_address'],
                abi=enterprise_abi
            )
            
            logger.info("Enterprise contract loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load enterprise contract: {e}")
    
    async def sync_enterprise_clients(self):
        """Sync enterprise clients from smart contract"""
        try:
            # Get all client registration events from contract
            # This would filter events from the enterprise contract
            
            # For now, simulate with test data
            test_clients = [
                {
                    "client_address": "0x1234567890123456789012345678901234567890",
                    "company_name": "AI Startup Co",
                    "contact_email": "cto@aistartup.com",
                    "tier": EnterpriseTier.STARTUP.value,
                    "contract_type": ContractType.MONTHLY.value,
                    "total_spent": 15000.0,
                    "total_hours": 300,
                    "joined_at": time.time() - (30 * 24 * 60 * 60)  # 30 days ago
                },
                {
                    "client_address": "0x2345678901234567890123456789012345678901", 
                    "company_name": "Gaming Studio LLC",
                    "contact_email": "ops@gamingstudio.com",
                    "tier": EnterpriseTier.PROFESSIONAL.value,
                    "contract_type": ContractType.QUARTERLY.value,
                    "total_spent": 75000.0,
                    "total_hours": 1200,
                    "joined_at": time.time() - (90 * 24 * 60 * 60)  # 90 days ago
                },
                {
                    "client_address": "0x3456789012345678901234567890123456789012",
                    "company_name": "Enterprise AI Corp",
                    "contact_email": "procurement@enterpriseai.com", 
                    "tier": EnterpriseTier.ENTERPRISE.value,
                    "contract_type": ContractType.ANNUAL.value,
                    "total_spent": 250000.0,
                    "total_hours": 4000,
                    "joined_at": time.time() - (180 * 24 * 60 * 60)  # 180 days ago
                }
            ]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for client in test_clients:
                cursor.execute('''
                    INSERT OR REPLACE INTO enterprise_clients 
                    (client_address, company_name, contact_email, tier, contract_type, 
                     total_spent, total_hours, joined_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    client["client_address"],
                    client["company_name"], 
                    client["contact_email"],
                    client["tier"],
                    client["contract_type"],
                    client["total_spent"],
                    client["total_hours"],
                    client["joined_at"],
                    True
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Synced {len(test_clients)} enterprise clients")
            
        except Exception as e:
            logger.error(f"Error syncing enterprise clients: {e}")
    
    async def calculate_revenue_metrics(self) -> RevenueMetrics:
        """Calculate comprehensive revenue metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total enterprise revenue
            cursor.execute('SELECT SUM(total_spent) FROM enterprise_clients WHERE is_active = TRUE')
            total_revenue = cursor.fetchone()[0] or 0
            
            # Get active client count
            cursor.execute('SELECT COUNT(*) FROM enterprise_clients WHERE is_active = TRUE')
            active_clients = cursor.fetchone()[0] or 0
            
            # Calculate average revenue per client
            avg_revenue_per_client = total_revenue / active_clients if active_clients > 0 else 0
            
            # Calculate monthly recurring revenue (MRR)
            thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
            cursor.execute('''
                SELECT SUM(amount) FROM revenue_transactions 
                WHERE timestamp > ? AND timestamp <= ?
            ''', (thirty_days_ago, time.time()))
            mrr = cursor.fetchone()[0] or 0
            
            # Calculate annual contract value (ACV)
            cursor.execute('''
                SELECT SUM(total_spent) FROM enterprise_clients 
                WHERE contract_type IN (?, ?) AND is_active = TRUE
            ''', (ContractType.ANNUAL.value, ContractType.QUARTERLY.value))
            acv = cursor.fetchone()[0] or 0
            
            # Calculate growth rate (month over month)
            sixty_days_ago = time.time() - (60 * 24 * 60 * 60)
            cursor.execute('''
                SELECT SUM(amount) FROM revenue_transactions 
                WHERE timestamp > ? AND timestamp <= ?
            ''', (sixty_days_ago, thirty_days_ago))
            prev_month_revenue = cursor.fetchone()[0] or 1
            
            growth_rate = ((mrr - prev_month_revenue) / prev_month_revenue * 100) if prev_month_revenue > 0 else 0
            
            # Calculate churn rate (simplified)
            cursor.execute('SELECT COUNT(*) FROM enterprise_clients WHERE is_active = FALSE')
            churned_clients = cursor.fetchone()[0] or 0
            total_clients = active_clients + churned_clients
            churn_rate = (churned_clients / total_clients * 100) if total_clients > 0 else 0
            
            conn.close()
            
            metrics = RevenueMetrics(
                timestamp=time.time(),
                total_enterprise_revenue=total_revenue,
                active_enterprise_clients=active_clients,
                average_revenue_per_client=avg_revenue_per_client,
                monthly_recurring_revenue=mrr,
                annual_contract_value=acv,
                client_acquisition_cost=5000.0,  # Estimated CAC
                client_lifetime_value=avg_revenue_per_client * 24,  # Estimated 24-month LTV
                churn_rate=churn_rate,
                growth_rate=growth_rate
            )
            
            # Store metrics in history
            await self._store_revenue_metrics(metrics)
            
            # Add to in-memory history
            self.revenue_history.append(metrics)
            if len(self.revenue_history) > 1000:
                self.revenue_history.pop(0)
            
            logger.info(f"Calculated revenue metrics: ${total_revenue:.2f} total, {active_clients} clients")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating revenue metrics: {e}")
            return RevenueMetrics(
                timestamp=time.time(),
                total_enterprise_revenue=0,
                active_enterprise_clients=0,
                average_revenue_per_client=0,
                monthly_recurring_revenue=0,
                annual_contract_value=0,
                client_acquisition_cost=0,
                client_lifetime_value=0,
                churn_rate=0,
                growth_rate=0
            )
    
    async def _store_revenue_metrics(self, metrics: RevenueMetrics):
        """Store revenue metrics in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO revenue_metrics_history 
                (timestamp, total_enterprise_revenue, active_enterprise_clients, 
                 average_revenue_per_client, monthly_recurring_revenue, 
                 annual_contract_value, growth_rate, churn_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.total_enterprise_revenue,
                metrics.active_enterprise_clients,
                metrics.average_revenue_per_client,
                metrics.monthly_recurring_revenue,
                metrics.annual_contract_value,
                metrics.growth_rate,
                metrics.churn_rate
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing revenue metrics: {e}")
    
    async def get_client_performance(self, client_address: str) -> Optional[ClientPerformance]:
        """Get detailed performance metrics for a specific client"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get client details
            cursor.execute('''
                SELECT company_name, tier, total_spent, total_hours 
                FROM enterprise_clients WHERE client_address = ?
            ''', (client_address,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return None
            
            company_name, tier, total_spent, total_hours = result
            
            # Get payment history
            cursor.execute('''
                SELECT amount, discount_applied, gpu_hours, timestamp 
                FROM revenue_transactions 
                WHERE client_address = ? 
                ORDER BY timestamp DESC LIMIT 10
            ''', (client_address,))
            
            payments = []
            total_discounts = 0
            for amount, discount, hours, timestamp in cursor.fetchall():
                payments.append({
                    "amount": amount,
                    "discount": discount,
                    "hours": hours,
                    "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                })
                total_discounts += discount
            
            # Calculate monthly average
            months_active = max(1, (time.time() - time.time() + (90 * 24 * 60 * 60)) / (30 * 24 * 60 * 60))
            monthly_average = total_spent / months_active
            
            # Calculate usage trends (simplified)
            usage_trends = {
                "gpu_hours_trend": "increasing" if total_hours > 100 else "stable",
                "spending_trend": "increasing" if monthly_average > 10000 else "stable",
                "efficiency_trend": "improving" if total_discounts > 1000 else "stable"
            }
            
            conn.close()
            
            return ClientPerformance(
                client_address=client_address,
                company_name=company_name,
                tier=EnterpriseTier(tier).name,
                total_revenue=total_spent,
                monthly_average=monthly_average,
                gpu_hours_used=total_hours,
                discount_savings=total_discounts,
                payment_history=payments,
                usage_trends=usage_trends,
                satisfaction_score=95.0  # Simulated high satisfaction
            )
            
        except Exception as e:
            logger.error(f"Error getting client performance for {client_address}: {e}")
            return None
    
    async def generate_revenue_dashboard(self) -> Dict:
        """Generate comprehensive revenue dashboard data"""
        try:
            # Get current metrics
            current_metrics = await self.calculate_revenue_metrics()
            
            # Get top clients
            top_clients = await self._get_top_clients(5)
            
            # Get tier distribution
            tier_distribution = await self._get_tier_distribution()
            
            # Get revenue trends
            revenue_trends = await self._get_revenue_trends(30)  # Last 30 days
            
            # Get growth projections
            growth_projections = await self._calculate_growth_projections()
            
            dashboard = {
                "timestamp": datetime.now().isoformat(),
                "current_metrics": asdict(current_metrics),
                "top_clients": top_clients,
                "tier_distribution": tier_distribution,
                "revenue_trends": revenue_trends,
                "growth_projections": growth_projections,
                "key_insights": self._generate_insights(current_metrics),
                "recommendations": self._generate_recommendations(current_metrics)
            }
            
            logger.info(f"Generated revenue dashboard with {len(top_clients)} top clients")
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating revenue dashboard: {e}")
            return {"error": str(e)}
    
    async def _get_top_clients(self, limit: int) -> List[Dict]:
        """Get top clients by revenue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT client_address, company_name, tier, total_spent, total_hours
                FROM enterprise_clients 
                WHERE is_active = TRUE 
                ORDER BY total_spent DESC 
                LIMIT ?
            ''', (limit,))
            
            clients = []
            for row in cursor.fetchall():
                clients.append({
                    "address": row[0],
                    "company": row[1],
                    "tier": EnterpriseTier(row[2]).name,
                    "revenue": row[3],
                    "hours": row[4]
                })
            
            conn.close()
            return clients
            
        except Exception as e:
            logger.error(f"Error getting top clients: {e}")
            return []
    
    async def _get_tier_distribution(self) -> Dict[str, int]:
        """Get client distribution by tier"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tier, COUNT(*) 
                FROM enterprise_clients 
                WHERE is_active = TRUE 
                GROUP BY tier
            ''')
            
            distribution = {}
            for tier_num, count in cursor.fetchall():
                tier_name = EnterpriseTier(tier_num).name
                distribution[tier_name] = count
            
            conn.close()
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting tier distribution: {e}")
            return {}
    
    async def _get_revenue_trends(self, days: int) -> List[Dict]:
        """Get revenue trends over specified days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            cursor.execute('''
                SELECT DATE(timestamp, 'unixepoch') as date, SUM(amount) as daily_revenue
                FROM revenue_transactions 
                WHERE timestamp > ?
                GROUP BY DATE(timestamp, 'unixepoch')
                ORDER BY date
            ''', (cutoff_time,))
            
            trends = []
            for date, revenue in cursor.fetchall():
                trends.append({
                    "date": date,
                    "revenue": revenue
                })
            
            conn.close()
            return trends
            
        except Exception as e:
            logger.error(f"Error getting revenue trends: {e}")
            return []
    
    async def _calculate_growth_projections(self) -> Dict:
        """Calculate growth projections based on current trends"""
        if not self.revenue_history or len(self.revenue_history) < 2:
            return {"next_month": 0, "next_quarter": 0, "next_year": 0}
        
        # Simple linear projection based on recent growth
        recent_growth = self.revenue_history[-1].growth_rate
        current_mrr = self.revenue_history[-1].monthly_recurring_revenue
        
        projections = {
            "next_month": current_mrr * (1 + recent_growth / 100),
            "next_quarter": current_mrr * 3 * (1 + recent_growth / 100),
            "next_year": current_mrr * 12 * (1 + recent_growth / 100)
        }
        
        return projections
    
    def _generate_insights(self, metrics: RevenueMetrics) -> List[str]:
        """Generate key insights from revenue metrics"""
        insights = []
        
        if metrics.growth_rate > 20:
            insights.append(f"🚀 Exceptional growth: {metrics.growth_rate:.1f}% month-over-month")
        elif metrics.growth_rate > 10:
            insights.append(f"📈 Strong growth: {metrics.growth_rate:.1f}% month-over-month")
        elif metrics.growth_rate < 0:
            insights.append(f"⚠️ Revenue declining: {metrics.growth_rate:.1f}% month-over-month")
        
        if metrics.churn_rate < 5:
            insights.append(f"✅ Excellent retention: {metrics.churn_rate:.1f}% churn rate")
        elif metrics.churn_rate > 15:
            insights.append(f"🚨 High churn alert: {metrics.churn_rate:.1f}% churn rate")
        
        if metrics.average_revenue_per_client > 50000:
            insights.append(f"💎 High-value clients: ${metrics.average_revenue_per_client:.0f} average revenue")
        
        if metrics.active_enterprise_clients > 100:
            insights.append(f"🏢 Scale achieved: {metrics.active_enterprise_clients} enterprise clients")
        
        return insights
    
    def _generate_recommendations(self, metrics: RevenueMetrics) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if metrics.growth_rate < 10:
            recommendations.append("Focus on client acquisition campaigns to increase growth rate")
        
        if metrics.churn_rate > 10:
            recommendations.append("Implement customer success program to reduce churn")
        
        if metrics.average_revenue_per_client < 25000:
            recommendations.append("Upsell existing clients to higher-tier plans")
        
        if metrics.active_enterprise_clients < 50:
            recommendations.append("Launch enterprise sales blitz to reach 100+ clients")
        
        recommendations.append("Consider implementing dynamic pricing based on demand")
        recommendations.append("Expand institutional staking programs for larger deals")
        
        return recommendations
    
    async def start_revenue_monitoring(self):
        """Start continuous revenue monitoring"""
        logger.info("🚀 Starting enterprise revenue monitoring with MAXIMUM VELOCITY!")
        
        while True:
            try:
                # Sync clients from blockchain
                await self.sync_enterprise_clients()
                
                # Calculate and store metrics
                await self.calculate_revenue_metrics()
                
                # Sleep for an hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Revenue monitoring error: {e}")
                await asyncio.sleep(60)

# Example usage
if __name__ == "__main__":
    import os
    config = {
        'database_path': 'enterprise_revenue.db',
        'rpc_url': os.getenv('RPC_URL', 'http://localhost:8545'),
        'enterprise_contract_address': os.getenv('GPUDX_ENTERPRISE_V2_ADDRESS', '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0'),
    }
    
    dashboard = EnterpriseRevenueDashboard(config)
    
    async def test_dashboard():
        # Sync clients and generate dashboard
        await dashboard.sync_enterprise_clients()
        revenue_data = await dashboard.generate_revenue_dashboard()
        
        print("📊 Enterprise Revenue Dashboard:")
        print(f"Total Revenue: ${revenue_data['current_metrics']['total_enterprise_revenue']:,.2f}")
        print(f"Active Clients: {revenue_data['current_metrics']['active_enterprise_clients']}")
        print(f"Growth Rate: {revenue_data['current_metrics']['growth_rate']:.1f}%")
        print(f"Churn Rate: {revenue_data['current_metrics']['churn_rate']:.1f}%")
        
        print("\n🎯 Key Insights:")
        for insight in revenue_data['key_insights']:
            print(f"  {insight}")
        
        print("\n💡 Recommendations:")
        for rec in revenue_data['recommendations']:
            print(f"  • {rec}")
    
    # Instead of just running test, start FastAPI server
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Initialize dashboard service
    dashboard_service = EnterpriseRevenueDashboard(config)
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx Enterprise Revenue Dashboard", version="2.0.0")
    
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
        return {"message": "GPUDx Enterprise Revenue Dashboard", "status": "operational"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "enterprise_dashboard"}
    
    @app.get("/status")
    async def status():
        return {"status": "operational", "service": "enterprise_revenue_dashboard", "version": "2.0.0"}
    
    @app.get("/revenue")
    async def get_revenue_dashboard():
        """Get current revenue dashboard data"""
        await dashboard_service.sync_enterprise_clients()
        return await dashboard_service.generate_revenue_dashboard()
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        if generate_latest:
            from fastapi import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        else:
            # Fallback if prometheus_client isn't available
            return {"error": "Prometheus client not available", "service": "enterprise_dashboard"}
    
    # Start the server
    port = int(os.getenv('ENTERPRISE_DASHBOARD_PORT', '8002'))
    uvicorn.run(app, host="0.0.0.0", port=port) 