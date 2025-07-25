import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from database import DatabaseManager
from providers import CloudProviderIntegrator
from email_service import email_service

logger = logging.getLogger(__name__)

class AlertChecker:
    def __init__(self, check_interval: int = 300):  # 5 minutes default
        self.check_interval = check_interval
        self.aggregator = CloudProviderIntegrator()
        self.running = False
    
    async def start(self):
        """Start the alert checking service."""
        self.running = True
        logger.info("Alert checker service started")
        
        while self.running:
            try:
                await self.check_and_notify_alerts()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in alert checker: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def stop(self):
        """Stop the alert checking service."""
        self.running = False
        logger.info("Alert checker service stopped")
    
    async def check_and_notify_alerts(self):
        """Check all active alerts and send notifications."""
        try:
            db_manager = DatabaseManager()
            
            # Get all active alerts
            active_alerts = self._get_active_alerts(db_manager)
            
            if not active_alerts:
                logger.debug("No active alerts to check")
                db_manager.close()
                return
            
            logger.info(f"Checking {len(active_alerts)} active alerts")
            
            # Group alerts by GPU type for efficient price fetching
            alerts_by_gpu = {}
            for alert in active_alerts:
                gpu_type = alert['gpu_type']
                if gpu_type not in alerts_by_gpu:
                    alerts_by_gpu[gpu_type] = []
                alerts_by_gpu[gpu_type].append(alert)
            
            # Check each GPU type
            for gpu_type, gpu_alerts in alerts_by_gpu.items():
                await self._check_gpu_alerts(gpu_type, gpu_alerts, db_manager)
            
            db_manager.close()
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _get_active_alerts(self, db_manager: DatabaseManager) -> List[Dict]:
        """Get all active alerts that haven't been triggered recently."""
        try:
            # Get alerts that are active and either never triggered or triggered >1 hour ago
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            from database import Alert
            alerts = db_manager.db.query(Alert).filter(
                Alert.is_active == True,
                Alert.notifications_enabled == True,
                (Alert.triggered_at.is_(None) | (Alert.triggered_at < one_hour_ago))
            ).all()
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def _check_gpu_alerts(self, gpu_type: str, alerts: List[Dict], db_manager: DatabaseManager):
        """Check alerts for a specific GPU type."""
        try:
            # Get current prices for this GPU
            prices = await self.aggregator.aggregate_all_prices(gpu_type, "us-east")
            
            if not prices or 'providers' not in prices:
                logger.warning(f"No price data available for {gpu_type}")
                return
            
            # Find the best (lowest) price
            best_price = None
            best_provider = None
            
            for provider_data in prices['providers']:
                if provider_data['price'] is not None:
                    if best_price is None or provider_data['price'] < best_price:
                        best_price = provider_data['price']
                        best_provider = provider_data['provider']
            
            if best_price is None:
                logger.warning(f"No valid prices found for {gpu_type}")
                return
            
            logger.info(f"Best price for {gpu_type}: ${best_price:.2f}/hr from {best_provider}")
            
            # Check each alert for this GPU
            for alert in alerts:
                target_price = alert['target_price']
                
                # If current price is at or below target, send notification
                if best_price <= target_price:
                    savings = target_price - best_price
                    
                    await self._send_price_alert(
                        alert, best_price, best_provider, savings, db_manager
                    )
                    
        except Exception as e:
            logger.error(f"Error checking {gpu_type} alerts: {e}")
    
    async def _send_price_alert(self, alert: Dict, current_price: float, 
                               provider: str, savings: float, db_manager: DatabaseManager):
        """Send price alert notification."""
        try:
            # Send email notification
            success = await email_service.send_price_alert(
                email=alert['email'],
                gpu_type=alert['gpu_type'],
                target_price=alert['target_price'],
                current_price=current_price,
                provider=provider,
                savings=savings
            )
            
            if success:
                # Update alert as triggered
                self._mark_alert_triggered(alert['id'], db_manager)
                logger.info(f"Price alert sent to {alert['email']} for {alert['gpu_type']}")
            else:
                logger.error(f"Failed to send price alert to {alert['email']}")
                
        except Exception as e:
            logger.error(f"Error sending price alert: {e}")
    
    def _mark_alert_triggered(self, alert_id: int, db_manager: DatabaseManager):
        """Mark an alert as triggered."""
        try:
            from database import Alert
            alert = db_manager.db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.triggered_at = datetime.utcnow()
                db_manager.db.commit()
                logger.debug(f"Marked alert {alert_id} as triggered")
        except Exception as e:
            logger.error(f"Error marking alert as triggered: {e}")

# Global alert checker instance
alert_checker = AlertChecker()

async def start_alert_service():
    """Start the alert checking service."""
    await alert_checker.start()

async def stop_alert_service():
    """Stop the alert checking service."""
    await alert_checker.stop() 