"""
AI Optimization Service - Bill Gates on Adderall Technical Excellence
Advanced ML/AI system for portfolio optimization, risk assessment, and market intelligence
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, create_engine, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

Base = declarative_base()

@dataclass
class MarketPrediction:
    gpu_model: str
    predicted_price: float
    confidence_score: float
    trend_direction: str  # 'up', 'down', 'stable'
    optimal_timing: datetime
    risk_score: float

@dataclass
class PortfolioOptimization:
    current_allocation: Dict[str, float]
    optimal_allocation: Dict[str, float]
    expected_return: float
    risk_score: float
    rebalance_actions: List[Dict[str, Any]]

@dataclass
class RiskAssessment:
    overall_risk_score: float  # 0-100
    volatility_risk: float
    liquidity_risk: float
    concentration_risk: float
    market_risk: float
    recommendations: List[str]

class AIModel(Base):
    __tablename__ = "ai_models"
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)  # 'price_prediction', 'risk_assessment', 'portfolio_optimization'
    model_version = Column(String(20), nullable=False)
    
    # Model Performance
    accuracy_score = Column(Float, default=0.0)
    mae_score = Column(Float, default=0.0)
    r2_score = Column(Float, default=0.0)
    
    # Model Metadata
    training_data_size = Column(Integer, default=0)
    feature_count = Column(Integer, default=0)
    training_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Model Configuration
    hyperparameters = Column(JSON)
    feature_importance = Column(JSON)
    model_metrics = Column(JSON)
    
    is_active = Column(Boolean, default=True)
    performance_threshold = Column(Float, default=0.85)

class MarketData(Base):
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True)
    gpu_model = Column(String(100), nullable=False, index=True)
    provider = Column(String(100), nullable=False)
    
    # Pricing Data
    price_per_hour = Column(Float, nullable=False)
    currency = Column(String(10), default='USD')
    
    # Performance Metrics
    cuda_cores = Column(Integer)
    memory_gb = Column(Integer)
    memory_bandwidth = Column(Float)
    compute_capability = Column(String(10))
    
    # Market Metrics
    availability = Column(Boolean, default=True)
    demand_score = Column(Float, default=0.0)  # 0-100
    utilization_rate = Column(Float, default=0.0)  # 0-1
    
    # External Factors
    region = Column(String(50))
    datacenter = Column(String(100))
    network_latency = Column(Integer)  # milliseconds
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    data_source = Column(String(50))
    is_verified = Column(Boolean, default=True)

class UserPortfolio(Base):
    __tablename__ = "user_portfolios"
    
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(42), index=True, nullable=False)
    
    # Portfolio Composition
    gpu_allocations = Column(JSON)  # {"RTX_4090": 0.4, "H100": 0.6}
    risk_tolerance = Column(Float, default=0.5)  # 0-1 (conservative to aggressive)
    investment_horizon = Column(Integer, default=365)  # days
    
    # Performance Tracking
    total_value_usd = Column(Float, default=0.0)
    daily_return = Column(Float, default=0.0)
    monthly_return = Column(Float, default=0.0)
    ytd_return = Column(Float, default=0.0)
    
    # Risk Metrics
    volatility = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    var_95 = Column(Float, default=0.0)  # Value at Risk (95%)
    
    # AI Recommendations
    optimization_score = Column(Float, default=0.0)  # 0-100
    last_optimization = Column(DateTime)
    next_rebalance = Column(DateTime)
    
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow)

class AIOptimizationService:
    def __init__(self):
        self.db = self._initialize_database()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # ML Models (in-memory for fast inference)
        self.price_prediction_model = None
        self.volatility_model = None
        self.demand_prediction_model = None
        self.risk_assessment_model = None
        
        # Model scalers
        self.price_scaler = StandardScaler()
        self.demand_scaler = StandardScaler()
        self.risk_scaler = StandardScaler()
        
        # Market data cache
        self.market_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("AIOptimizationService initialized - Bill Gates on Adderall mode activated")
    
    def _initialize_database(self):
        """Initialize database connection"""
        database_url = os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        engine = create_engine(database_url)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
async def predict_gpu_prices(self, gpu_models: List[str], timeframe_hours: int = 24) -> List[MarketPrediction]:
        """AI-powered GPU price prediction"""
        try:
            predictions = []
            
            for gpu_model in gpu_models:
                # Get historical data
                historical_data = await self._get_historical_market_data(gpu_model, days=30)
                
                if len(historical_data) < 50:  # Need sufficient data
                    continue
                
                # Prepare features
                features = self._prepare_price_features(historical_data)
                
                # Make prediction
                if self.price_prediction_model is None:
                    await self._train_price_prediction_model()
                
                prediction = self.price_prediction_model.predict(features[-1:])
                confidence = self._calculate_prediction_confidence(features, prediction[0])
                
                # Determine trend
                recent_prices = [d['price_per_hour'] for d in historical_data[-10:]]
                trend = self._analyze_trend(recent_prices, prediction[0])
                
                # Calculate risk score
                volatility = np.std(recent_prices) / np.mean(recent_prices)
                risk_score = min(100, volatility * 100)
                
                predictions.append(MarketPrediction(
                    gpu_model=gpu_model,
                    predicted_price=float(prediction[0]),
                    confidence_score=confidence,
                    trend_direction=trend,
                    optimal_timing=datetime.utcnow() + timedelta(hours=timeframe_hours),
                    risk_score=risk_score
                ))
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting GPU prices: {e}")
            return []
    
async def optimize_portfolio(self, wallet_address: str) -> PortfolioOptimization:
        """Advanced portfolio optimization using modern portfolio theory"""
        try:
            # Get current portfolio
            portfolio = self.db.query(UserPortfolio).filter(
                UserPortfolio.wallet_address == wallet_address
            ).first()
            
            if not portfolio:
                # Create default portfolio
                portfolio = UserPortfolio(
                    wallet_address=wallet_address,
                    gpu_allocations={"RTX_4090": 1.0},
                    risk_tolerance=0.5
                )
                self.db.add(portfolio)
                self.db.commit()
            
            current_allocation = portfolio.gpu_allocations
            risk_tolerance = portfolio.risk_tolerance
            
            # Get market data for all GPU models
            gpu_models = list(current_allocation.keys())
            market_data = {}
            
            for gpu_model in gpu_models:
                historical_data = await self._get_historical_market_data(gpu_model, days=90)
                market_data[gpu_model] = historical_data
            
            # Calculate expected returns and covariance matrix
            returns_data = self._calculate_returns_matrix(market_data)
            expected_returns = self._calculate_expected_returns(returns_data)
            covariance_matrix = self._calculate_covariance_matrix(returns_data)
            
            # Optimize portfolio using Markowitz optimization
            optimal_weights = self._markowitz_optimization(
                expected_returns, 
                covariance_matrix, 
                risk_tolerance
            )
            
            # Convert to allocation dictionary
            optimal_allocation = {}
            for i, gpu_model in enumerate(gpu_models):
                optimal_allocation[gpu_model] = float(optimal_weights[i])
            
            # Calculate expected return and risk
            portfolio_return = np.dot(optimal_weights, expected_returns)
            portfolio_risk = np.sqrt(np.dot(optimal_weights.T, np.dot(covariance_matrix, optimal_weights)))
            
            # Generate rebalancing actions
            rebalance_actions = []
            for gpu_model in gpu_models:
                current_weight = current_allocation.get(gpu_model, 0)
                optimal_weight = optimal_allocation.get(gpu_model, 0)
                diff = optimal_weight - current_weight
                
                if abs(diff) > 0.05:  # 5% threshold
                    action = "increase" if diff > 0 else "decrease"
                    rebalance_actions.append({
                        "gpu_model": gpu_model,
                        "action": action,
                        "current_allocation": current_weight,
                        "target_allocation": optimal_weight,
                        "change_required": abs(diff)
                    })
            
            return PortfolioOptimization(
                current_allocation=current_allocation,
                optimal_allocation=optimal_allocation,
                expected_return=float(portfolio_return * 100),  # Convert to percentage
                risk_score=float(portfolio_risk * 100),
                rebalance_actions=rebalance_actions
            )
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return PortfolioOptimization(
                current_allocation={},
                optimal_allocation={},
                expected_return=0.0,
                risk_score=0.0,
                rebalance_actions=[]
            )
    
async def assess_risk(self, wallet_address: str, gpu_allocations: Dict[str, float]) -> RiskAssessment:
        """Comprehensive risk assessment using advanced metrics"""
        try:
            risks = {
                'volatility_risk': 0.0,
                'liquidity_risk': 0.0,
                'concentration_risk': 0.0,
                'market_risk': 0.0
            }
            
            recommendations = []
            
            # 1. Volatility Risk Assessment
            total_volatility = 0.0
            for gpu_model, weight in gpu_allocations.items():
                historical_data = await self._get_historical_market_data(gpu_model, days=30)
                if historical_data:
                    prices = [d['price_per_hour'] for d in historical_data]
                    volatility = np.std(prices) / np.mean(prices) if prices else 0
                    total_volatility += weight * volatility
            
            risks['volatility_risk'] = min(100, total_volatility * 100)
            
            if risks['volatility_risk'] > 50:
                recommendations.append("Consider reducing exposure to high-volatility GPU models")
            
            # 2. Concentration Risk Assessment
            max_allocation = max(gpu_allocations.values()) if gpu_allocations else 0
            risks['concentration_risk'] = max_allocation * 100
            
            if risks['concentration_risk'] > 60:
                recommendations.append("Portfolio is too concentrated - consider diversifying across more GPU models")
            
            # 3. Liquidity Risk Assessment
            avg_liquidity = 0.0
            for gpu_model, weight in gpu_allocations.items():
                # Get recent market data to assess liquidity
                recent_data = await self._get_recent_market_activity(gpu_model)
                liquidity_score = self._calculate_liquidity_score(recent_data)
                avg_liquidity += weight * liquidity_score
            
            risks['liquidity_risk'] = max(0, 100 - avg_liquidity)
            
            if risks['liquidity_risk'] > 40:
                recommendations.append("Some GPU models have low liquidity - consider more liquid alternatives")
            
            # 4. Market Risk Assessment
            market_correlation = await self._calculate_market_correlation(gpu_allocations)
            risks['market_risk'] = market_correlation * 100
            
            if risks['market_risk'] > 70:
                recommendations.append("Portfolio is highly correlated with overall market - consider counter-cyclical assets")
            
            # Calculate overall risk score
            overall_risk = np.mean(list(risks.values()))
            
            return RiskAssessment(
                overall_risk_score=float(overall_risk),
                volatility_risk=float(risks['volatility_risk']),
                liquidity_risk=float(risks['liquidity_risk']),
                concentration_risk=float(risks['concentration_risk']),
                market_risk=float(risks['market_risk']),
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            return RiskAssessment(
                overall_risk_score=0.0,
                volatility_risk=0.0,
                liquidity_risk=0.0,
                concentration_risk=0.0,
                market_risk=0.0,
                recommendations=["Error calculating risk - please try again"]
            )
    
async def generate_market_intelligence(self, gpu_models: List[str]) -> Dict[str, Any]:
        """Generate comprehensive market intelligence report"""
        try:
            intelligence = {
                'market_overview': {},
                'demand_analysis': {},
                'supply_analysis': {},
                'competitive_landscape': {},
                'recommendations': []
            }
            
            for gpu_model in gpu_models:
                # Market overview
                historical_data = await self._get_historical_market_data(gpu_model, days=30)
                current_price = historical_data[-1]['price_per_hour'] if historical_data else 0
                
                # Calculate price trends
                if len(historical_data) >= 7:
                    week_ago_price = historical_data[-7]['price_per_hour']
                    price_change = (current_price - week_ago_price) / week_ago_price * 100
                else:
                    price_change = 0
                
                # Demand analysis
                demand_score = await self._calculate_demand_score(gpu_model)
                
                # Supply analysis
                supply_metrics = await self._analyze_supply_metrics(gpu_model)
                
                intelligence['market_overview'][gpu_model] = {
                    'current_price': current_price,
                    'price_change_7d': price_change,
                    'demand_score': demand_score,
                    'supply_availability': supply_metrics['availability'],
                    'market_cap': supply_metrics['total_capacity']
                }
            
            # Generate strategic recommendations
            intelligence['recommendations'] = await self._generate_strategic_recommendations(intelligence)
            
            return intelligence
            
        except Exception as e:
            logger.error(f"Error generating market intelligence: {e}")
            return {'error': str(e)}
    
    # Helper methods for AI calculations
    
async def _get_historical_market_data(self, gpu_model: str, days: int = 30) -> List[Dict]:
        """Get historical market data for GPU model"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        market_data = self.db.query(MarketData).filter(
            MarketData.gpu_model == gpu_model,
            MarketData.timestamp >= start_date,
            MarketData.timestamp <= end_date
        ).order_by(MarketData.timestamp.asc()).all()
        
        return [
            {
                'price_per_hour': data.price_per_hour,
                'demand_score': data.demand_score,
                'utilization_rate': data.utilization_rate,
                'availability': data.availability,
                'timestamp': data.timestamp
            }
            for data in market_data
        ]
    
    def _prepare_price_features(self, historical_data: List[Dict]) -> np.ndarray:
        """Prepare features for price prediction model"""
        df = pd.DataFrame(historical_data)
        
        # Technical indicators
        df['price_ma_7'] = df['price_per_hour'].rolling(window=7).mean()
        df['price_ma_14'] = df['price_per_hour'].rolling(window=14).mean()
        df['price_volatility'] = df['price_per_hour'].rolling(window=7).std()
        df['demand_ma_7'] = df['demand_score'].rolling(window=7).mean()
        df['utilization_ma_7'] = df['utilization_rate'].rolling(window=7).mean()
        
        # Feature selection
        features = [
            'price_ma_7', 'price_ma_14', 'price_volatility',
            'demand_ma_7', 'utilization_ma_7', 'demand_score', 'utilization_rate'
        ]
        
        return df[features].fillna(0).values
    
async def _train_price_prediction_model(self):
        """Train the price prediction model"""
        try:
            # This would be expanded with more sophisticated training
            # For now, using a simple RandomForest
            self.price_prediction_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            # In production, this would load pre-trained models
            logger.info("Price prediction model initialized")
            
        except Exception as e:
            logger.error(f"Error training price prediction model: {e}")
    
    def _calculate_prediction_confidence(self, features: np.ndarray, prediction: float) -> float:
        """Calculate confidence score for prediction"""
        # Simplified confidence calculation
        # In production, this would use ensemble methods
        return min(1.0, max(0.6, 1.0 - abs(prediction - np.mean(features[-10:, 0])) / np.std(features[-10:, 0])))
    
    def _analyze_trend(self, recent_prices: List[float], predicted_price: float) -> str:
        """Analyze price trend direction"""
        if len(recent_prices) < 3:
            return 'stable'
        
        current_price = recent_prices[-1]
        trend_threshold = 0.05  # 5%
        
        change = (predicted_price - current_price) / current_price
        
        if change > trend_threshold:
            return 'up'
        elif change < -trend_threshold:
            return 'down'
        else:
            return 'stable'
    
    def _calculate_returns_matrix(self, market_data: Dict[str, List[Dict]]) -> pd.DataFrame:
        """Calculate returns matrix for portfolio optimization"""
        returns_data = {}
        
        for gpu_model, data in market_data.items():
            prices = [d['price_per_hour'] for d in data]
            returns = np.diff(np.log(prices)) if len(prices) > 1 else [0]
            returns_data[gpu_model] = returns
        
        return pd.DataFrame(returns_data).fillna(0)
    
    def _calculate_expected_returns(self, returns_data: pd.DataFrame) -> np.ndarray:
        """Calculate expected returns for each asset"""
        return returns_data.mean().values
    
    def _calculate_covariance_matrix(self, returns_data: pd.DataFrame) -> np.ndarray:
        """Calculate covariance matrix"""
        return returns_data.cov().values
    
    def _markowitz_optimization(self, expected_returns: np.ndarray, covariance_matrix: np.ndarray, risk_tolerance: float) -> np.ndarray:
        """Markowitz portfolio optimization"""
        # Simplified optimization - in production would use scipy.optimize
        n_assets = len(expected_returns)
        
        # Equal weight as starting point
        weights = np.ones(n_assets) / n_assets
        
        # Simple adjustment based on risk tolerance
        # Higher risk tolerance = more weight to higher return assets
        if risk_tolerance > 0.5:
            # Favor higher expected returns
            weights = expected_returns / np.sum(expected_returns)
        
        return weights
    
async def _get_recent_market_activity(self, gpu_model: str) -> Dict:
        """Get recent market activity for liquidity assessment"""
        # Simplified - would get real trading volume data
        return {'trading_volume': 100, 'order_book_depth': 50}
    
    def _calculate_liquidity_score(self, market_activity: Dict) -> float:
        """Calculate liquidity score based on market activity"""
        # Simplified liquidity scoring
        volume = market_activity.get('trading_volume', 0)
        depth = market_activity.get('order_book_depth', 0)
        
        liquidity_score = min(100, (volume + depth) / 2)
        return liquidity_score
    
async def _calculate_market_correlation(self, gpu_allocations: Dict[str, float]) -> float:
        """Calculate overall market correlation"""
        # Simplified correlation calculation
        # In production, would calculate correlation with market indices
        return 0.7  # Placeholder
    
async def _calculate_demand_score(self, gpu_model: str) -> float:
        """Calculate demand score for GPU model"""
        recent_data = await self._get_historical_market_data(gpu_model, days=7)
        if not recent_data:
            return 50.0
        
        avg_utilization = np.mean([d['utilization_rate'] for d in recent_data])
        avg_demand = np.mean([d['demand_score'] for d in recent_data])
        
        return (avg_utilization * 100 + avg_demand) / 2
    
async def _analyze_supply_metrics(self, gpu_model: str) -> Dict:
        """Analyze supply metrics for GPU model"""
        recent_data = await self._get_historical_market_data(gpu_model, days=7)
        if not recent_data:
            return {'availability': 50.0, 'total_capacity': 0}
        
        availability = np.mean([d['availability'] for d in recent_data]) * 100
        total_capacity = len([d for d in recent_data if d['availability']])
        
        return {
            'availability': availability,
            'total_capacity': total_capacity
        }
    
async def _generate_strategic_recommendations(self, intelligence: Dict) -> List[str]:
        """Generate strategic recommendations based on market intelligence"""
        recommendations = []
        
        # Analyze market overview to generate recommendations
        market_overview = intelligence.get('market_overview', {})
        
        for gpu_model, metrics in market_overview.items():
            price_change = metrics.get('price_change_7d', 0)
            demand_score = metrics.get('demand_score', 0)
            
            if price_change > 10:
                recommendations.append(f"{gpu_model}: Consider taking profits - price up {price_change:.1f}% this week")
            elif price_change < -10:
                recommendations.append(f"{gpu_model}: Potential buying opportunity - price down {price_change:.1f}% this week")
            
            if demand_score > 80:
                recommendations.append(f"{gpu_model}: High demand detected - consider increasing allocation")
            elif demand_score < 30:
                recommendations.append(f"{gpu_model}: Low demand - consider reducing exposure")
        
        return recommendations

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
        'port': int(os.getenv('AI_OPTIMIZATION_PORT', '8008'))
    }
    
    # Initialize AI optimization service
    ai_service = AIOptimizationService()
    
    # Create FastAPI app
    app = FastAPI(title="GPUDx AI Optimization Service", version="2.0.0")

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
        return {"message": "GPUDx AI Optimization Service", "status": "operational"}
    
@app.get("/health")
async def health():
        return {"status": "healthy", "service": "ai_optimization"}
    
@app.get("/metrics")
async def metrics():
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from fastapi import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return {"error": "Prometheus client not available", "service": "ai_optimization"}
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=config['port']) 
