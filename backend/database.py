# Database models and configuration for GPUDex

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gpudex.db")

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, index=True)
    gpu_type = Column(String, index=True)
    price = Column(Float)
    region = Column(String)
    availability = Column(String)
    instance_type = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "gpu_type": self.gpu_type,
            "price": self.price,
            "region": self.region,
            "availability": self.availability,
            "instance_type": self.instance_type,
            "timestamp": self.timestamp.isoformat()
        }

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    gpu_type = Column(String, index=True)
    target_price = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    welcome_sent = Column(Boolean, default=False)
    notifications_enabled = Column(Boolean, default=True)
    region = Column(String, default="us-east")
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "email": self.email,
            "gpu_type": self.gpu_type,
            "target_price": self.target_price,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "welcome_sent": self.welcome_sent,
            "notifications_enabled": self.notifications_enabled,
            "region": self.region
        }

class ProviderStats(Base):
    __tablename__ = "provider_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, index=True)
    total_instances = Column(Integer, default=0)
    average_price = Column(Float, default=0.0)
    reliability_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "total_instances": self.total_instances,
            "average_price": self.average_price,
            "reliability_score": self.reliability_score,
            "last_updated": self.last_updated.isoformat()
        }

# Create tables
def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# Database session dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseManager:
    def __init__(self):
        self.db = SessionLocal()
    
    def save_prices(self, prices: List[Dict], gpu_type: str):
        """Save price data to database"""
        try:
            for price_data in prices:
                price_record = PriceHistory(
                    provider=price_data['provider'],
                    gpu_type=gpu_type,
                    price=price_data['price'],
                    region=price_data.get('region', 'unknown'),
                    availability=price_data.get('availability', 'unknown'),
                    instance_type=price_data.get('type', 'unknown')
                )
                self.db.add(price_record)
            
            self.db.commit()
            logger.info(f"Saved {len(prices)} price records for {gpu_type}")
        except Exception as e:
            logger.error(f"Error saving prices: {e}")
            self.db.rollback()
    
    def create_alert(self, email: str, gpu_type: str, target_price: float) -> Dict:
        """Create a new price alert"""
        try:
            alert = Alert(
                email=email,
                gpu_type=gpu_type,
                target_price=target_price
            )
            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)
            logger.info(f"Created alert for {email} - {gpu_type} below ${target_price}")
            return alert.to_dict()
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            self.db.rollback()
            raise
    
    def get_price_history(self, gpu_type: str, provider: str = None, hours: int = 24) -> List[Dict]:
        """Get price history for a GPU type"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = self.db.query(PriceHistory).filter(
                PriceHistory.gpu_type == gpu_type,
                PriceHistory.timestamp >= cutoff_time
            )
            
            if provider:
                query = query.filter(PriceHistory.provider == provider)
            
            history = query.order_by(PriceHistory.timestamp.desc()).all()
            return [record.to_dict() for record in history]
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return []
    
    def get_average_price(self, gpu_type: str, provider: str = None, hours: int = 24) -> float:
        """Get average price for a GPU type"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = self.db.query(PriceHistory).filter(
                PriceHistory.gpu_type == gpu_type,
                PriceHistory.timestamp >= cutoff_time
            )
            
            if provider:
                query = query.filter(PriceHistory.provider == provider)
            
            result = self.db.query(func.avg(PriceHistory.price)).filter(
                PriceHistory.gpu_type == gpu_type,
                PriceHistory.timestamp >= cutoff_time
            ).scalar()
            
            return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Error getting average price: {e}")
            return 0.0
    
    def check_alerts(self, gpu_type: str, current_price: float) -> List[Dict]:
        """Check if any alerts should be triggered"""
        try:
            alerts = self.db.query(Alert).filter(
                Alert.gpu_type == gpu_type,
                Alert.is_active == True,
                Alert.target_price >= current_price
            ).all()
            
            triggered_alerts = []
            for alert in alerts:
                alert.is_active = False
                alert.triggered_at = datetime.utcnow()
                triggered_alerts.append(alert.to_dict())
            
            self.db.commit()
            return triggered_alerts
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            self.db.rollback()
            return []
    
    def get_user_alerts(self, email: str) -> List[Dict]:
        """Get all alerts for a user."""
        try:
            alerts = self.db.query(Alert).filter(Alert.email == email).all()
            return [alert.to_dict() for alert in alerts]
        except Exception as e:
            logger.error(f"Error getting user alerts: {e}")
            return []
    
    def update_alert_welcome_status(self, alert_id: int, welcome_sent: bool) -> bool:
        """Update welcome email sent status for an alert."""
        try:
            alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.welcome_sent = welcome_sent
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update welcome status: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        self.db.close()

# Database manager
db_manager = DatabaseManager()

# Create all tables
def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")

# Initialize tables when module is imported
create_tables() 