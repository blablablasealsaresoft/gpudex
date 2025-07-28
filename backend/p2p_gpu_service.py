"""
P2P GPU Lending Service
Allows individuals to list their GPUs and earn $GPUDX tokens
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

Base = declarative_base()

@dataclass
class GPUBenchmark:
    cuda_cores: int
    memory_gb: int
    memory_bandwidth: float
    base_clock: int
    boost_clock: int
    compute_capability: str
    hashrate_eth: Optional[float] = None
    hashrate_btc: Optional[float] = None

@dataclass 
class GPUPerformanceScore:
    gaming_score: int  # 0-100
    ml_training_score: int  # 0-100
    inference_score: int  # 0-100
    rendering_score: int  # 0-100
    mining_score: int  # 0-100
    overall_score: int  # 0-100

class GPUProvider(Base):
    __tablename__ = "gpu_providers"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    
    # Profile Info
    bio = Column(Text)
    location = Column(String(100))
    timezone = Column(String(50))
    languages = Column(String(200))  # JSON array of language codes
    
    # Reputation System
    reputation_score = Column(Float, default=0.0)  # 0-1000
    total_rentals = Column(Integer, default=0)
    successful_rentals = Column(Integer, default=0)
    total_hours_provided = Column(Float, default=0.0)
    average_rating = Column(Float, default=0.0)  # 0-5 stars
    
    # Earnings
    total_earnings_gpudx = Column(Float, default=0.0)
    total_earnings_usd = Column(Float, default=0.0)
    current_month_earnings = Column(Float, default=0.0)
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    joined_date = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # KYC/Verification
    kyc_status = Column(String(20), default='pending')  # pending, verified, rejected
    verification_documents = Column(Text)  # JSON of document hashes

class GPUListing(Base):
    __tablename__ = "gpu_listings"
    
    id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, nullable=False, index=True)
    
    # Hardware Details
    gpu_model = Column(String(100), nullable=False)  # "RTX 4090", "H100", etc.
    gpu_brand = Column(String(50), nullable=False)   # "NVIDIA", "AMD"
    gpu_memory = Column(Integer, nullable=False)      # Memory in GB
    quantity = Column(Integer, default=1)
    
    # Technical Specs (JSON)
    specifications = Column(JSON)  # Detailed GPU specs
    benchmarks = Column(JSON)      # Performance benchmarks
    performance_scores = Column(JSON)  # Gaming, ML, rendering scores
    
    # System Info
    cpu_model = Column(String(100))
    ram_gb = Column(Integer)
    storage_type = Column(String(20))  # "SSD", "NVMe", "HDD"
    internet_speed = Column(Integer)    # Mbps
    
    # Pricing
    hourly_rate_gpudx = Column(Float, nullable=False)
    hourly_rate_usd = Column(Float, nullable=False)
    minimum_rental_hours = Column(Integer, default=1)
    maximum_rental_hours = Column(Integer, default=168)  # 1 week
    
    # Availability
    is_available = Column(Boolean, default=True)
    availability_schedule = Column(JSON)  # Weekly schedule
    timezone = Column(String(50))
    
    # Location & Latency
    country = Column(String(50))
    region = Column(String(50))
    datacenter = Column(String(100))
    estimated_latency_ms = Column(Integer)
    
    # Features
    supports_docker = Column(Boolean, default=True)
    supports_jupyter = Column(Boolean, default=True)
    supports_ssh = Column(Boolean, default=True)
    custom_software = Column(Text)  # JSON array of supported software
    
    # Economics
    power_cost_kwh = Column(Float, default=0.0)
    monthly_revenue_target = Column(Float, default=0.0)
    profit_margin = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    total_rental_hours = Column(Float, default=0.0)
    total_earnings = Column(Float, default=0.0)

class GPURental(Base):
    __tablename__ = "gpu_rentals"
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, nullable=False, index=True)
    provider_id = Column(Integer, nullable=False, index=True)
    renter_address = Column(String(42), nullable=False, index=True)
    
    # Rental Details
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    actual_end_time = Column(DateTime)
    total_hours = Column(Float, nullable=False)
    
    # Payment
    total_cost_gpudx = Column(Float, nullable=False)
    total_cost_usd = Column(Float, nullable=False)
    platform_fee_gpudx = Column(Float, nullable=False)
    provider_earnings_gpudx = Column(Float, nullable=False)
    payment_transaction_hash = Column(String(66))
    
    # Status
    status = Column(String(20), default='pending')  # pending, active, completed, cancelled, disputed
    
    # Performance Monitoring
    uptime_percentage = Column(Float, default=0.0)
    average_utilization = Column(Float, default=0.0)
    performance_issues = Column(Text)  # JSON array of issues
    
    # Review & Rating
    renter_rating = Column(Integer)  # 1-5 stars
    renter_review = Column(Text)
    provider_rating = Column(Integer)  # 1-5 stars  
    provider_review = Column(Text)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow)

class P2PGPUService:
    def __init__(self):
        self.db = self._initialize_database()
        
        # GPU performance database (simplified)
        self.gpu_performance_db = {
            'RTX 4090': {
                'cuda_cores': 16384,
                'memory_gb': 24,
                'gaming_score': 100,
                'ml_training_score': 95,
                'inference_score': 90,
                'rendering_score': 100,
                'base_price_usd': 2.5
            },
            'RTX 4080': {
                'cuda_cores': 9728,
                'memory_gb': 16,
                'gaming_score': 90,
                'ml_training_score': 85,
                'inference_score': 80,
                'rendering_score': 90,
                'base_price_usd': 1.8
            },
            'H100': {
                'cuda_cores': 16896,
                'memory_gb': 80,
                'gaming_score': 70,
                'ml_training_score': 100,
                'inference_score': 100,
                'rendering_score': 85,
                'base_price_usd': 4.0
            }
        }
        
        logger.info("P2PGPUService initialized")
    
    def _initialize_database(self):
        """Initialize database connection"""
        database_url = os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        engine = create_engine(database_url)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    async def register_gpu_provider(self, wallet_address: str, username: str, email: str, profile_data: Dict) -> Dict[str, Any]:
        """Register a new GPU provider"""
        try:
            # Check if provider already exists
            existing = self.db.query(GPUProvider).filter(
                GPUProvider.wallet_address == wallet_address
            ).first()
            
            if existing:
                return {'success': False, 'error': 'Provider already registered'}
            
            # Create new provider
            provider = GPUProvider(
                wallet_address=wallet_address,
                username=username,
                email=email,
                bio=profile_data.get('bio', ''),
                location=profile_data.get('location', ''),
                timezone=profile_data.get('timezone', 'UTC'),
                languages=json.dumps(profile_data.get('languages', ['en']))
            )
            
            self.db.add(provider)
            self.db.commit()
            
            return {
                'success': True,
                'provider_id': provider.id,
                'message': 'GPU provider registered successfully'
            }
            
        except Exception as e:
            logger.error(f"Error registering GPU provider: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def create_gpu_listing(self, provider_address: str, gpu_data: Dict) -> Dict[str, Any]:
        """Create a new GPU listing"""
        try:
            # Get provider
            provider = self.db.query(GPUProvider).filter(
                GPUProvider.wallet_address == provider_address
            ).first()
            
            if not provider:
                return {'success': False, 'error': 'Provider not found'}
            
            # Get GPU performance data
            gpu_model = gpu_data['gpu_model']
            gpu_specs = self.gpu_performance_db.get(gpu_model, {})
            
            # Calculate suggested pricing
            base_price = gpu_specs.get('base_price_usd', 1.0)
            performance_multiplier = gpu_specs.get('ml_training_score', 50) / 50
            suggested_price = base_price * performance_multiplier
            
            # Create listing
            listing = GPUListing(
                provider_id=provider.id,
                gpu_model=gpu_model,
                gpu_brand=gpu_data.get('gpu_brand', 'NVIDIA'),
                gpu_memory=gpu_data.get('gpu_memory', 8),
                quantity=gpu_data.get('quantity', 1),
                specifications=gpu_specs,
                hourly_rate_gpudx=gpu_data.get('hourly_rate_gpudx', suggested_price),
                hourly_rate_usd=gpu_data.get('hourly_rate_usd', suggested_price),
                cpu_model=gpu_data.get('cpu_model', ''),
                ram_gb=gpu_data.get('ram_gb', 32),
                country=gpu_data.get('country', ''),
                region=gpu_data.get('region', ''),
                supports_docker=gpu_data.get('supports_docker', True),
                supports_jupyter=gpu_data.get('supports_jupyter', True),
                supports_ssh=gpu_data.get('supports_ssh', True)
            )
            
            self.db.add(listing)
            self.db.commit()
            
            return {
                'success': True,
                'listing_id': listing.id,
                'suggested_price_usd': suggested_price,
                'performance_score': gpu_specs.get('ml_training_score', 0),
                'message': 'GPU listing created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating GPU listing: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def search_available_gpus(self, search_params: Dict) -> List[Dict[str, Any]]:
        """Search for available GPU listings"""
        try:
            query = self.db.query(GPUListing).filter(
                GPUListing.is_available == True,
                GPUListing.is_active == True
            )
            
            # Apply filters
            if search_params.get('gpu_model'):
                query = query.filter(GPUListing.gpu_model.ilike(f"%{search_params['gpu_model']}%"))
            
            if search_params.get('min_memory'):
                query = query.filter(GPUListing.gpu_memory >= search_params['min_memory'])
            
            if search_params.get('max_price_usd'):
                query = query.filter(GPUListing.hourly_rate_usd <= search_params['max_price_usd'])
            
            if search_params.get('country'):
                query = query.filter(GPUListing.country == search_params['country'])
            
            # Sort by price or performance
            sort_by = search_params.get('sort_by', 'price')
            if sort_by == 'price':
                query = query.order_by(GPUListing.hourly_rate_usd.asc())
            elif sort_by == 'performance':
                # Would need to sort by performance score from JSON
                query = query.order_by(GPUListing.gpu_memory.desc())
            
            listings = query.limit(50).all()
            
            # Format results
            results = []
            for listing in listings:
                # Get provider info
                provider = self.db.query(GPUProvider).filter(
                    GPUProvider.id == listing.provider_id
                ).first()
                
                results.append({
                    'listing_id': listing.id,
                    'gpu_model': listing.gpu_model,
                    'gpu_memory': listing.gpu_memory,
                    'quantity': listing.quantity,
                    'hourly_rate_gpudx': listing.hourly_rate_gpudx,
                    'hourly_rate_usd': listing.hourly_rate_usd,
                    'provider_username': provider.username if provider else 'Unknown',
                    'provider_reputation': provider.reputation_score if provider else 0,
                    'provider_rating': provider.average_rating if provider else 0,
                    'location': f"{listing.country}, {listing.region}",
                    'availability': 'Available',
                    'specifications': listing.specifications,
                    'supports_features': {
                        'docker': listing.supports_docker,
                        'jupyter': listing.supports_jupyter,
                        'ssh': listing.supports_ssh
                    }
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching GPUs: {e}")
            return []
    
    async def rent_gpu(self, renter_address: str, listing_id: int, rental_data: Dict) -> Dict[str, Any]:
        """Process GPU rental request"""
        try:
            # Get listing
            listing = self.db.query(GPUListing).filter(
                GPUListing.id == listing_id,
                GPUListing.is_available == True
            ).first()
            
            if not listing:
                return {'success': False, 'error': 'GPU listing not available'}
            
            # Calculate rental cost
            hours = rental_data['hours']
            total_cost_gpudx = listing.hourly_rate_gpudx * hours
            total_cost_usd = listing.hourly_rate_usd * hours
            
            # Calculate platform fee (3%)
            platform_fee = total_cost_gpudx * 0.03
            provider_earnings = total_cost_gpudx - platform_fee
            
            # Create rental record
            rental = GPURental(
                listing_id=listing_id,
                provider_id=listing.provider_id,
                renter_address=renter_address,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=hours),
                total_hours=hours,
                total_cost_gpudx=total_cost_gpudx,
                total_cost_usd=total_cost_usd,
                platform_fee_gpudx=platform_fee,
                provider_earnings_gpudx=provider_earnings,
                status='pending'
            )
            
            self.db.add(rental)
            self.db.commit()
            
            return {
                'success': True,
                'rental_id': rental.id,
                'total_cost_gpudx': total_cost_gpudx,
                'total_cost_usd': total_cost_usd,
                'platform_fee': platform_fee,
                'provider_earnings': provider_earnings,
                'start_time': rental.start_time.isoformat(),
                'end_time': rental.end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing GPU rental: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    async def get_provider_dashboard(self, provider_address: str) -> Dict[str, Any]:
        """Get provider dashboard data"""
        try:
            provider = self.db.query(GPUProvider).filter(
                GPUProvider.wallet_address == provider_address
            ).first()
            
            if not provider:
                return {'error': 'Provider not found'}
            
            # Get listings
            listings = self.db.query(GPUListing).filter(
                GPUListing.provider_id == provider.id
            ).all()
            
            # Get recent rentals
            recent_rentals = self.db.query(GPURental).filter(
                GPURental.provider_id == provider.id
            ).order_by(GPURental.created_date.desc()).limit(10).all()
            
            # Calculate earnings this month
            start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_earnings = self.db.query(GPURental).filter(
                GPURental.provider_id == provider.id,
                GPURental.created_date >= start_of_month,
                GPURental.status == 'completed'
            ).all()
            
            monthly_gpudx = sum(r.provider_earnings_gpudx for r in monthly_earnings)
            monthly_usd = sum(r.total_cost_usd * 0.97 for r in monthly_earnings)  # 97% after 3% fee
            
            return {
                'provider_info': {
                    'username': provider.username,
                    'reputation_score': provider.reputation_score,
                    'total_rentals': provider.total_rentals,
                    'success_rate': (provider.successful_rentals / max(provider.total_rentals, 1)) * 100,
                    'average_rating': provider.average_rating,
                    'total_earnings_gpudx': provider.total_earnings_gpudx,
                    'total_earnings_usd': provider.total_earnings_usd,
                    'joined_date': provider.joined_date.isoformat()
                },
                'monthly_stats': {
                    'earnings_gpudx': monthly_gpudx,
                    'earnings_usd': monthly_usd,
                    'rentals_count': len(monthly_earnings),
                    'hours_provided': sum(r.total_hours for r in monthly_earnings)
                },
                'active_listings': len([l for l in listings if l.is_active]),
                'total_listings': len(listings),
                'recent_rentals': [
                    {
                        'rental_id': r.id,
                        'gpu_model': 'GPU Model',  # Would need to join with listing
                        'hours': r.total_hours,
                        'earnings': r.provider_earnings_gpudx,
                        'status': r.status,
                        'start_time': r.start_time.isoformat()
                    } for r in recent_rentals
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting provider dashboard: {e}")
            return {'error': str(e)}

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
        'port': int(os.getenv('P2P_GPU_PORT', '8006'))
    }
    
    # Initialize P2P service
    p2p_service = P2PGPUService()
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx P2P GPU Service", version="2.0.0")

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
        return {"message": "GPUDx P2P GPU Service", "status": "operational"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "p2p_gpu"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from fastapi import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return {"error": "Prometheus client not available", "service": "p2p_gpu"}
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=config['port']) 
