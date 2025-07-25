import os
import logging
from typing import List, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'alerts@gpudex.com')
        self.client = None
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        if self.api_key:
            self.client = SendGridAPIClient(api_key=self.api_key)
            logger.info("SendGrid email service initialized")
        else:
            logger.warning("SendGrid API key not found. Email notifications disabled.")
    
    async def send_price_alert(self, 
                              email: str, 
                              gpu_type: str, 
                              target_price: float, 
                              current_price: float, 
                              provider: str,
                              savings: float) -> bool:
        """Send price alert email when target price is reached."""
        
        if not self.client:
            logger.info(f"Email service disabled. Would send alert to {email}")
            return False
        
        try:
            # Create email content
            subject = f"🎯 GPU Price Alert: {gpu_type.upper()} Now ${current_price:.2f}/hr!"
            
            html_content = self._create_alert_html(
                gpu_type, target_price, current_price, provider, savings
            )
            
            text_content = self._create_alert_text(
                gpu_type, target_price, current_price, provider, savings
            )
            
            # Send email
            message = Mail(
                from_email=From(self.from_email, "GPUDex Price Alerts"),
                to_emails=To(email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(text_content),
                html_content=HtmlContent(html_content)
            )
            
            # Send asynchronously
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor, 
                self._send_email_sync, 
                message
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Price alert sent successfully to {email}")
                return True
            else:
                logger.error(f"Failed to send email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return False
    
    def _send_email_sync(self, message):
        """Synchronous email sending for executor."""
        return self.client.send(message)
    
    async def send_welcome_email(self, email: str) -> bool:
        """Send welcome email when user signs up for alerts."""
        
        if not self.client:
            logger.info(f"Would send welcome email to {email}")
            return False
        
        try:
            subject = "Welcome to GPUDex Price Alerts! 🚀"
            
            html_content = self._create_welcome_html()
            text_content = self._create_welcome_text()
            
            message = Mail(
                from_email=From(self.from_email, "GPUDex Team"),
                to_emails=To(email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(text_content),
                html_content=HtmlContent(html_content)
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor, 
                self._send_email_sync, 
                message
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Welcome email sent to {email}")
                return True
            else:
                logger.error(f"Failed to send welcome email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Welcome email failed: {str(e)}")
            return False
    
    def _create_alert_html(self, gpu_type: str, target_price: float, 
                          current_price: float, provider: str, savings: float) -> str:
        """Create HTML content for price alert email."""
        
        savings_percent = (target_price - current_price) / target_price * 100
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>GPU Price Alert</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .alert-box {{ background: #dcfce7; border: 2px solid #16a34a; border-radius: 8px; padding: 20px; margin: 20px 0; }}
                .price-large {{ font-size: 2.5em; font-weight: bold; color: #16a34a; }}
                .savings {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ background: #f9fafb; padding: 20px; text-align: center; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Price Alert Triggered!</h1>
                    <p>Your target price for {gpu_type.upper()} has been reached</p>
                </div>
                
                <div class="content">
                    <div class="alert-box">
                        <h2 style="margin-top: 0; color: #16a34a;">Target Price Reached!</h2>
                        <div class="price-large">${current_price:.2f}/hr</div>
                        <p><strong>Provider:</strong> {provider}</p>
                        <p><strong>GPU:</strong> {gpu_type.upper()}</p>
                    </div>
                    
                    <div class="savings">
                        <h3 style="margin-top: 0;">💰 You're Saving Money!</h3>
                        <p><strong>Your target:</strong> ${target_price:.2f}/hr</p>
                        <p><strong>Current price:</strong> ${current_price:.2f}/hr</p>
                        <p><strong>Savings:</strong> ${savings:.2f}/hr ({savings_percent:.1f}% below target)</p>
                    </div>
                    
                    <a href="https://gpudex.vercel.app/?gpu={gpu_type}" class="button">
                        🚀 Deploy Now
                    </a>
                    
                    <p><em>Act fast! GPU prices change frequently. This deal might not last long.</em></p>
                </div>
                
                <div class="footer">
                    <p>GPUDex - Find The Best GPU Prices Instantly</p>
                    <p>You're receiving this because you set up a price alert.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_alert_text(self, gpu_type: str, target_price: float, 
                          current_price: float, provider: str, savings: float) -> str:
        """Create plain text content for price alert email."""
        
        savings_percent = (target_price - current_price) / target_price * 100
        
        return f"""
🎯 GPU PRICE ALERT

Your target price for {gpu_type.upper()} has been reached!

CURRENT DEAL:
- Price: ${current_price:.2f}/hr
- Provider: {provider}
- GPU: {gpu_type.upper()}

SAVINGS:
- Target: ${target_price:.2f}/hr
- Current: ${current_price:.2f}/hr
- You save: ${savings:.2f}/hr ({savings_percent:.1f}% below target)

Deploy now: https://gpudex.vercel.app/?gpu={gpu_type}

Act fast! GPU prices change frequently.

---
GPUDex - Find The Best GPU Prices Instantly
        """
    
    def _create_welcome_html(self) -> str:
        """Create HTML welcome email."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to GPUDex</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
                .content { padding: 30px; }
                .feature { display: flex; align-items: center; margin: 15px 0; }
                .feature-icon { font-size: 1.5em; margin-right: 15px; }
                .button { display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
                .footer { background: #f9fafb; padding: 20px; text-align: center; color: #6b7280; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to GPUDex! 🚀</h1>
                    <p>You're now part of the smartest GPU price community</p>
                </div>
                
                <div class="content">
                    <h2>Thanks for joining our price alerts!</h2>
                    
                    <p>You'll now receive notifications when GPU prices drop below your targets. Here's what makes GPUDex special:</p>
                    
                    <div class="feature">
                        <span class="feature-icon">⚡</span>
                        <div>
                            <strong>Real-time price monitoring</strong><br>
                            We track 13+ providers 24/7
                        </div>
                    </div>
                    
                    <div class="feature">
                        <span class="feature-icon">💰</span>
                        <div>
                            <strong>Arbitrage detection</strong><br>
                            Find price differences up to 76% savings
                        </div>
                    </div>
                    
                    <div class="feature">
                        <span class="feature-icon">📊</span>
                        <div>
                            <strong>Price history charts</strong><br>
                            Track trends and make informed decisions
                        </div>
                    </div>
                    
                    <a href="https://gpudex.vercel.app/" class="button">
                        🎯 Start Finding Deals
                    </a>
                    
                    <p><strong>Pro tip:</strong> Set multiple alerts for different GPU types to never miss a great deal!</p>
                </div>
                
                <div class="footer">
                    <p>GPUDex - Find The Best GPU Prices Instantly</p>
                    <p>Happy hunting! 🎯</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_welcome_text(self) -> str:
        """Create plain text welcome email."""
        return """
🚀 Welcome to GPUDex!

Thanks for joining our price alerts! You're now part of the smartest GPU price community.

WHAT YOU GET:
⚡ Real-time price monitoring across 13+ providers
💰 Arbitrage detection with up to 76% savings
📊 Interactive price history charts
🎯 Instant alerts when prices drop

Pro tip: Set multiple alerts for different GPU types to never miss a great deal!

Start finding deals: https://gpudex.vercel.app/

Happy hunting! 🎯

---
GPUDex - Find The Best GPU Prices Instantly
        """

# Global email service instance
email_service = EmailService() 