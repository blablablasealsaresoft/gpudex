import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import os
import json
from dataclasses import dataclass
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class PricePrediction:
    gpu_type: str
    provider: str
    current_price: float
    predicted_price: float
    confidence_score: float
    prediction_horizon: str  # "1h", "24h", "7d", "30d"
    trend: str  # "up", "down", "stable"
    factors: Dict[str, float]  # Contributing factors
    timestamp: datetime

@dataclass
class MarketTrend:
    gpu_type: str
    trend_direction: str  # "bullish", "bearish", "neutral"
    strength: float  # 0-1
    volatility: float  # 0-1
    support_level: float
    resistance_level: float
    moving_average_7d: float
    moving_average_30d: float

class MLPredictionService:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        self.models = {}
        self.scalers = {}
        self.label_encoders = {}
        self.feature_importance = {}
        
        # Model configurations
        self.model_configs = {
            "short_term": {  # 1-24 hours
                "model": RandomForestRegressor(
                    n_estimators=100,
                    max_depth=15,
                    min_samples_split=5,
                    random_state=42
                ),
                "features": ["hour", "day_of_week", "provider_encoded", "gpu_encoded", 
                           "recent_avg", "volatility", "market_demand"]
            },
            "medium_term": {  # 1-7 days
                "model": GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=8,
                    random_state=42
                ),
                "features": ["day", "week_of_year", "provider_encoded", "gpu_encoded",
                           "weekly_avg", "trend_strength", "market_sentiment"]
            },
            "long_term": {  # 7-30 days
                "model": LinearRegression(),
                "features": ["month", "quarter", "provider_encoded", "gpu_encoded",
                           "monthly_avg", "seasonal_factor", "supply_demand_ratio"]
            }
        }
        
        # Initialize encoders
        self._initialize_encoders()
        
        logger.info("ML Prediction Service initialized")

    def _initialize_encoders(self):
        """Initialize label encoders for categorical variables"""
        # Common GPU types
        gpu_types = ["RTX 4090", "RTX 3090", "A100", "H100", "V100", "A40", "RTX 6000", "T4"]
        self.label_encoders["gpu"] = LabelEncoder()
        self.label_encoders["gpu"].fit(gpu_types)
        
        # Common providers
        providers = ["vast", "runpod", "aws", "gcp", "azure", "lambda", "paperspace", 
                    "tensordock", "vultr", "linode", "genesis", "coreweave", "crusoe"]
        self.label_encoders["provider"] = LabelEncoder()
        self.label_encoders["provider"].fit(providers)

    async def collect_historical_data(self, days: int = 30) -> pd.DataFrame:
        """Collect historical price data for training"""
        try:
            # This would typically query your price history table
            # For now, we'll generate synthetic data based on realistic patterns
            return self._generate_synthetic_data(days)
            
        except Exception as e:
            logger.error(f"Error collecting historical data: {e}")
            return pd.DataFrame()

    def _generate_synthetic_data(self, days: int) -> pd.DataFrame:
        """Generate synthetic price data for demonstration"""
        np.random.seed(42)
        
        data = []
        base_date = datetime.now() - timedelta(days=days)
        
        gpu_types = ["RTX 4090", "RTX 3090", "A100", "H100", "V100"]
        providers = ["vast", "runpod", "aws", "gcp", "azure", "lambda"]
        
        # Base prices for different GPU types
        base_prices = {
            "RTX 4090": 0.45,
            "RTX 3090": 0.35,
            "A100": 1.20,
            "H100": 2.50,
            "V100": 0.80
        }
        
        for day in range(days):
            for hour in range(24):
                timestamp = base_date + timedelta(days=day, hours=hour)
                
                for gpu in gpu_types:
                    for provider in providers:
                        # Generate realistic price with trends and noise
                        base_price = base_prices[gpu]
                        
                        # Add time-based patterns
                        hour_factor = 1 + 0.1 * np.sin(hour * np.pi / 12)  # Peak usage hours
                        day_factor = 1 + 0.05 * np.sin(day * 2 * np.pi / 7)  # Weekly pattern
                        
                        # Add provider-specific factors
                        provider_factors = {
                            "vast": 0.9, "runpod": 1.0, "aws": 1.5,
                            "gcp": 1.4, "azure": 1.6, "lambda": 1.1
                        }
                        provider_factor = provider_factors.get(provider, 1.0)
                        
                        # Add random noise
                        noise = np.random.normal(0, 0.05)
                        
                        # Calculate final price
                        price = base_price * hour_factor * day_factor * provider_factor * (1 + noise)
                        price = max(0.1, price)  # Ensure positive price
                        
                        data.append({
                            "timestamp": timestamp,
                            "gpu_type": gpu,
                            "provider": provider,
                            "price": price,
                            "hour": hour,
                            "day_of_week": timestamp.weekday(),
                            "day": timestamp.day,
                            "week_of_year": timestamp.isocalendar()[1],
                            "month": timestamp.month,
                            "quarter": (timestamp.month - 1) // 3 + 1
                        })
        
        df = pd.DataFrame(data)
        
        # Add derived features
        df = self._add_derived_features(df)
        
        return df

    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived features for better predictions"""
        # Sort by timestamp
        df = df.sort_values("timestamp")
        
        # Add moving averages
        for gpu in df["gpu_type"].unique():
            gpu_data = df[df["gpu_type"] == gpu].copy()
            gpu_data["recent_avg"] = gpu_data["price"].rolling(window=6).mean()  # 6-hour average
            gpu_data["weekly_avg"] = gpu_data["price"].rolling(window=168).mean()  # 7-day average
            gpu_data["monthly_avg"] = gpu_data["price"].rolling(window=720).mean()  # 30-day average
            
            # Calculate volatility
            gpu_data["volatility"] = gpu_data["price"].rolling(window=24).std()
            
            # Update main dataframe
            df.loc[df["gpu_type"] == gpu, "recent_avg"] = gpu_data["recent_avg"]
            df.loc[df["gpu_type"] == gpu, "weekly_avg"] = gpu_data["weekly_avg"]
            df.loc[df["gpu_type"] == gpu, "monthly_avg"] = gpu_data["monthly_avg"]
            df.loc[df["gpu_type"] == gpu, "volatility"] = gpu_data["volatility"]
        
        # Add market indicators (simplified)
        df["market_demand"] = np.random.uniform(0.5, 1.5, len(df))
        df["trend_strength"] = np.random.uniform(0, 1, len(df))
        df["market_sentiment"] = np.random.uniform(-1, 1, len(df))
        df["seasonal_factor"] = 1 + 0.1 * np.sin(df["month"] * 2 * np.pi / 12)
        df["supply_demand_ratio"] = np.random.uniform(0.8, 1.2, len(df))
        
        # Fill NaN values
        df = df.fillna(method="bfill").fillna(method="ffill")
        
        return df

    def _prepare_features(self, df: pd.DataFrame, model_type: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for training"""
        features = self.model_configs[model_type]["features"]
        
        # Create feature matrix
        X = df.copy()
        
        # Encode categorical variables
        if "gpu_encoded" in features:
            X["gpu_encoded"] = self.label_encoders["gpu"].transform(X["gpu_type"])
        
        if "provider_encoded" in features:
            X["provider_encoded"] = self.label_encoders["provider"].transform(X["provider"])
        
        # Select features
        X = X[features].values
        y = df["price"].values
        
        return X, y

    async def train_models(self, df: pd.DataFrame):
        """Train all prediction models"""
        logger.info("Starting model training...")
        
        for model_type, config in self.model_configs.items():
            try:
                logger.info(f"Training {model_type} model...")
                
                # Prepare data
                X, y = self._prepare_features(df, model_type)
                
                # Remove rows with NaN values
                mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
                X = X[mask]
                y = y[mask]
                
                if len(X) < 10:
                    logger.warning(f"Insufficient data for {model_type} model")
                    continue
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )
                
                # Scale features
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                
                # Train model
                model = config["model"]
                model.fit(X_train_scaled, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test_scaled)
                mae = mean_absolute_error(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                r2 = r2_score(y_test, y_pred)
                
                logger.info(f"{model_type} model performance - MAE: {mae:.4f}, RMSE: {rmse:.4f}, R²: {r2:.4f}")
                
                # Store model and scaler
                self.models[model_type] = model
                self.scalers[model_type] = scaler
                
                # Store feature importance (if available)
                if hasattr(model, "feature_importances_"):
                    self.feature_importance[model_type] = dict(
                        zip(config["features"], model.feature_importances_)
                    )
                
            except Exception as e:
                logger.error(f"Error training {model_type} model: {e}")

    async def predict_price(self, gpu_type: str, provider: str, horizon: str = "24h") -> Optional[PricePrediction]:
        """Predict future price for a specific GPU and provider"""
        try:
            # Determine model type based on horizon
            if horizon in ["1h", "6h", "12h", "24h"]:
                model_type = "short_term"
            elif horizon in ["2d", "3d", "7d"]:
                model_type = "medium_term"
            else:
                model_type = "long_term"
            
            if model_type not in self.models:
                logger.warning(f"Model {model_type} not trained")
                return None
            
            # Get current timestamp
            now = datetime.now()
            
            # Create feature vector
            features = self._create_prediction_features(gpu_type, provider, now, model_type)
            
            if features is None:
                return None
            
            # Make prediction
            model = self.models[model_type]
            scaler = self.scalers[model_type]
            
            features_scaled = scaler.transform([features])
            predicted_price = model.predict(features_scaled)[0]
            
            # Calculate confidence score (simplified)
            confidence_score = self._calculate_confidence(model_type, features)
            
            # Determine trend
            current_price = await self._get_current_price(gpu_type, provider)
            trend = "stable"
            if predicted_price > current_price * 1.05:
                trend = "up"
            elif predicted_price < current_price * 0.95:
                trend = "down"
            
            # Get contributing factors
            factors = self._get_prediction_factors(model_type, features)
            
            return PricePrediction(
                gpu_type=gpu_type,
                provider=provider,
                current_price=current_price,
                predicted_price=max(0.01, predicted_price),  # Ensure positive
                confidence_score=confidence_score,
                prediction_horizon=horizon,
                trend=trend,
                factors=factors,
                timestamp=now
            )
            
        except Exception as e:
            logger.error(f"Error predicting price: {e}")
            return None

    def _create_prediction_features(self, gpu_type: str, provider: str, timestamp: datetime, model_type: str) -> Optional[List[float]]:
        """Create feature vector for prediction"""
        try:
            features = []
            feature_names = self.model_configs[model_type]["features"]
            
            for feature in feature_names:
                if feature == "hour":
                    features.append(timestamp.hour)
                elif feature == "day_of_week":
                    features.append(timestamp.weekday())
                elif feature == "day":
                    features.append(timestamp.day)
                elif feature == "week_of_year":
                    features.append(timestamp.isocalendar()[1])
                elif feature == "month":
                    features.append(timestamp.month)
                elif feature == "quarter":
                    features.append((timestamp.month - 1) // 3 + 1)
                elif feature == "gpu_encoded":
                    try:
                        features.append(self.label_encoders["gpu"].transform([gpu_type])[0])
                    except ValueError:
                        features.append(0)  # Unknown GPU type
                elif feature == "provider_encoded":
                    try:
                        features.append(self.label_encoders["provider"].transform([provider])[0])
                    except ValueError:
                        features.append(0)  # Unknown provider
                else:
                    # For other features, use default values or estimates
                    features.append(self._get_default_feature_value(feature, gpu_type, provider))
            
            return features
            
        except Exception as e:
            logger.error(f"Error creating prediction features: {e}")
            return None

    def _get_default_feature_value(self, feature: str, gpu_type: str, provider: str) -> float:
        """Get default values for complex features"""
        defaults = {
            "recent_avg": 1.0,
            "weekly_avg": 1.0,
            "monthly_avg": 1.0,
            "volatility": 0.1,
            "market_demand": 1.0,
            "trend_strength": 0.5,
            "market_sentiment": 0.0,
            "seasonal_factor": 1.0,
            "supply_demand_ratio": 1.0
        }
        return defaults.get(feature, 0.0)

    def _calculate_confidence(self, model_type: str, features: List[float]) -> float:
        """Calculate prediction confidence score"""
        # Simplified confidence calculation
        # In practice, this could use prediction intervals, ensemble variance, etc.
        base_confidence = 0.7
        
        # Adjust based on feature quality
        if len(features) == len(self.model_configs[model_type]["features"]):
            base_confidence += 0.1
        
        # Add some randomness for demonstration
        confidence = base_confidence + np.random.uniform(-0.1, 0.1)
        return max(0.1, min(1.0, confidence))

    def _get_prediction_factors(self, model_type: str, features: List[float]) -> Dict[str, float]:
        """Get factors contributing to the prediction"""
        factors = {}
        
        if model_type in self.feature_importance:
            feature_names = self.model_configs[model_type]["features"]
            importance = self.feature_importance[model_type]
            
            for i, feature_name in enumerate(feature_names):
                if feature_name in importance:
                    factors[feature_name] = importance[feature_name]
        
        return factors

    async def _get_current_price(self, gpu_type: str, provider: str) -> float:
        """Get current price for GPU type and provider"""
        # This would query your current prices
        # For now, return a mock value
        base_prices = {
            "RTX 4090": 0.45,
            "RTX 3090": 0.35,
            "A100": 1.20,
            "H100": 2.50,
            "V100": 0.80
        }
        return base_prices.get(gpu_type, 1.0)

    async def analyze_market_trends(self, gpu_type: str) -> MarketTrend:
        """Analyze market trends for a specific GPU type"""
        try:
            # This would analyze historical data
            # For now, generate realistic mock data
            
            current_price = await self._get_current_price(gpu_type, "average")
            
            # Generate trend analysis
            trend_direction = np.random.choice(["bullish", "bearish", "neutral"], p=[0.3, 0.3, 0.4])
            strength = np.random.uniform(0.1, 0.9)
            volatility = np.random.uniform(0.05, 0.3)
            
            # Support and resistance levels
            support_level = current_price * np.random.uniform(0.85, 0.95)
            resistance_level = current_price * np.random.uniform(1.05, 1.15)
            
            # Moving averages
            ma_7d = current_price * np.random.uniform(0.95, 1.05)
            ma_30d = current_price * np.random.uniform(0.90, 1.10)
            
            return MarketTrend(
                gpu_type=gpu_type,
                trend_direction=trend_direction,
                strength=strength,
                volatility=volatility,
                support_level=support_level,
                resistance_level=resistance_level,
                moving_average_7d=ma_7d,
                moving_average_30d=ma_30d
            )
            
        except Exception as e:
            logger.error(f"Error analyzing market trends: {e}")
            return None

    async def get_price_alerts(self, threshold_change: float = 0.1) -> List[Dict[str, Any]]:
        """Get price alerts based on predictions"""
        alerts = []
        
        gpu_types = ["RTX 4090", "RTX 3090", "A100", "H100", "V100"]
        providers = ["vast", "runpod", "lambda"]
        
        for gpu in gpu_types:
            for provider in providers:
                prediction = await self.predict_price(gpu, provider, "24h")
                
                if prediction:
                    price_change = (prediction.predicted_price - prediction.current_price) / prediction.current_price
                    
                    if abs(price_change) >= threshold_change:
                        alerts.append({
                            "gpu_type": gpu,
                            "provider": provider,
                            "current_price": prediction.current_price,
                            "predicted_price": prediction.predicted_price,
                            "price_change_percent": price_change * 100,
                            "trend": prediction.trend,
                            "confidence": prediction.confidence_score,
                            "alert_type": "price_increase" if price_change > 0 else "price_decrease"
                        })
        
        return sorted(alerts, key=lambda x: abs(x["price_change_percent"]), reverse=True)

    async def save_models(self, model_dir: str = "models"):
        """Save trained models to disk"""
        try:
            os.makedirs(model_dir, exist_ok=True)
            
            for model_type, model in self.models.items():
                model_path = os.path.join(model_dir, f"{model_type}_model.joblib")
                joblib.dump(model, model_path)
                
                scaler_path = os.path.join(model_dir, f"{model_type}_scaler.joblib")
                joblib.dump(self.scalers[model_type], scaler_path)
            
            # Save encoders
            encoders_path = os.path.join(model_dir, "label_encoders.joblib")
            joblib.dump(self.label_encoders, encoders_path)
            
            # Save feature importance
            importance_path = os.path.join(model_dir, "feature_importance.json")
            with open(importance_path, 'w') as f:
                json.dump(self.feature_importance, f, indent=2)
            
            logger.info(f"Models saved to {model_dir}")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")

    async def load_models(self, model_dir: str = "models"):
        """Load trained models from disk"""
        try:
            for model_type in self.model_configs.keys():
                model_path = os.path.join(model_dir, f"{model_type}_model.joblib")
                scaler_path = os.path.join(model_dir, f"{model_type}_scaler.joblib")
                
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    self.models[model_type] = joblib.load(model_path)
                    self.scalers[model_type] = joblib.load(scaler_path)
            
            # Load encoders
            encoders_path = os.path.join(model_dir, "label_encoders.joblib")
            if os.path.exists(encoders_path):
                self.label_encoders = joblib.load(encoders_path)
            
            # Load feature importance
            importance_path = os.path.join(model_dir, "feature_importance.json")
            if os.path.exists(importance_path):
                with open(importance_path, 'r') as f:
                    self.feature_importance = json.load(f)
            
            logger.info(f"Models loaded from {model_dir}")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")

# Global ML service instance
ml_service = MLPredictionService()

# Background task to retrain models
async def retrain_models_task():
    """Background task to retrain models periodically"""
    while True:
        try:
            logger.info("Starting model retraining...")
            
            # Collect recent data
            df = await ml_service.collect_historical_data(days=30)
            
            if not df.empty:
                # Train models
                await ml_service.train_models(df)
                
                # Save models
                await ml_service.save_models()
                
                logger.info("Model retraining completed successfully")
            else:
                logger.warning("No data available for model retraining")
            
        except Exception as e:
            logger.error(f"Error in model retraining: {e}")
        
        # Wait 24 hours before next retraining
        await asyncio.sleep(86400)

def start_ml_service():
    """Start the ML service and background tasks"""
    asyncio.create_task(retrain_models_task())
    logger.info("ML Prediction Service started") 