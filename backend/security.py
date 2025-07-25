"""
GPUDex Security Module
Comprehensive security features including input validation, headers, and protection mechanisms.
"""

import os
import re
import html
import logging
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import bleach
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration and constants."""
    
    # Content Security Policy
    CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.stripe.com; "
        "frame-src https://js.stripe.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    # Allowed HTML tags for content sanitization
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'code', 'pre'
    ]
    
    ALLOWED_HTML_ATTRIBUTES = {
        'a': ['href', 'title'],
        'blockquote': ['cite'],
    }
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 100  # requests per hour
    BURST_RATE_LIMIT = 10    # requests per minute
    
    # Input validation
    MAX_STRING_LENGTH = 1000
    MAX_EMAIL_LENGTH = 255
    MAX_URL_LENGTH = 500
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        if not email or len(email) > SecurityConfig.MAX_EMAIL_LENGTH:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format and security."""
        if not url or len(url) > SecurityConfig.MAX_URL_LENGTH:
            return False
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check for suspicious patterns
            suspicious_patterns = [
                'javascript:', 'data:', 'vbscript:', 'file:', 'ftp:'
            ]
            
            if any(pattern in url.lower() for pattern in suspicious_patterns):
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = None) -> str:
        """Sanitize string input."""
        if not text:
            return ""
        
        # Set default max length
        if max_length is None:
            max_length = SecurityConfig.MAX_STRING_LENGTH
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # HTML escape
        text = html.escape(text)
        
        # Remove null bytes and control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text.strip()
    
    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """Sanitize HTML content."""
        if not html_content:
            return ""
        
        return bleach.clean(
            html_content,
            tags=SecurityConfig.ALLOWED_HTML_TAGS,
            attributes=SecurityConfig.ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def validate_gpu_type(gpu_type: str) -> bool:
        """Validate GPU type parameter."""
        if not gpu_type:
            return False
        
        # Allow alphanumeric, dash, underscore
        pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(pattern, gpu_type):
            return False
        
        # Check length
        if len(gpu_type) > 50:
            return False
        
        return True
    
    @staticmethod
    def validate_region(region: str) -> bool:
        """Validate region parameter."""
        if not region:
            return False
        
        # Allow alphanumeric, dash
        pattern = r'^[a-zA-Z0-9-]+$'
        if not re.match(pattern, region):
            return False
        
        # Check length
        if len(region) > 50:
            return False
        
        return True
    
    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None) -> bool:
        """Validate integer input."""
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                return False
            
            if max_val is not None and int_val > max_val:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False

class SecurityHeaders:
    """Security headers management."""
    
    @staticmethod
    def get_security_headers(request: Request) -> Dict[str, str]:
        """Get security headers based on request."""
        headers = SecurityConfig.SECURITY_HEADERS.copy()
        
        # Add CSP header
        headers["Content-Security-Policy"] = SecurityConfig.CSP_POLICY
        
        # Add CORS headers if needed
        origin = request.headers.get("origin")
        allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
        
        if origin and origin in allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        
        return headers

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""
    
    def __init__(self, app, trusted_proxies: List[str] = None):
        super().__init__(app)
        self.trusted_proxies = trusted_proxies or []
        self.rate_limiter = RateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with security checks."""
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        request.state.client_ip = client_ip
        
        # Security headers for response
        response = await call_next(request)
        
        # Add security headers
        security_headers = SecurityHeaders.get_security_headers(request)
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Get real client IP address."""
        
        # Check for forwarded headers from trusted proxies
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
            return client_ip
        
        # Check other headers
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"

class RateLimiter:
    """Advanced rate limiting with multiple strategies."""
    
    def __init__(self):
        self.request_counts = {}  # IP -> {timestamp: count}
        self.blocked_ips = {}     # IP -> block_until_timestamp
        
    def is_allowed(self, client_ip: str, endpoint: str = None) -> bool:
        """Check if request is allowed based on rate limiting."""
        
        # Check if IP is currently blocked
        if client_ip in self.blocked_ips:
            if datetime.utcnow().timestamp() < self.blocked_ips[client_ip]:
                return False
            else:
                # Unblock IP
                del self.blocked_ips[client_ip]
        
        # Get current timestamp (rounded to minute)
        current_minute = int(datetime.utcnow().timestamp() // 60)
        
        # Initialize tracking for IP
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {}
        
        # Clean old entries (older than 1 hour)
        cutoff_time = current_minute - 60
        self.request_counts[client_ip] = {
            timestamp: count for timestamp, count in self.request_counts[client_ip].items()
            if timestamp > cutoff_time
        }
        
        # Count requests in current minute
        current_count = self.request_counts[client_ip].get(current_minute, 0)
        
        # Check burst limit (per minute)
        if current_count >= SecurityConfig.BURST_RATE_LIMIT:
            # Block IP for 5 minutes
            self.blocked_ips[client_ip] = datetime.utcnow().timestamp() + 300
            logger.warning(f"IP {client_ip} blocked for burst rate limit violation")
            return False
        
        # Check hourly limit
        hourly_count = sum(self.request_counts[client_ip].values())
        if hourly_count >= SecurityConfig.DEFAULT_RATE_LIMIT:
            logger.warning(f"IP {client_ip} exceeded hourly rate limit")
            return False
        
        # Increment counter
        self.request_counts[client_ip][current_minute] = current_count + 1
        
        return True
    
    def get_rate_limit_info(self, client_ip: str) -> Dict[str, Any]:
        """Get rate limit information for client."""
        if client_ip not in self.request_counts:
            return {
                "requests_made": 0,
                "requests_remaining": SecurityConfig.DEFAULT_RATE_LIMIT,
                "reset_time": datetime.utcnow() + timedelta(hours=1)
            }
        
        current_minute = int(datetime.utcnow().timestamp() // 60)
        cutoff_time = current_minute - 60
        
        # Count recent requests
        recent_requests = sum(
            count for timestamp, count in self.request_counts[client_ip].items()
            if timestamp > cutoff_time
        )
        
        return {
            "requests_made": recent_requests,
            "requests_remaining": max(0, SecurityConfig.DEFAULT_RATE_LIMIT - recent_requests),
            "reset_time": datetime.utcnow() + timedelta(hours=1),
            "blocked": client_ip in self.blocked_ips
        }

class SQLInjectionDetector:
    """Detect potential SQL injection attempts."""
    
    SUSPICIOUS_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|;|/\*|\*/|xp_cmdshell)",
        r"(\b(or|and)\s+\d+\s*=\s*\d+)",
        r"(\b(or|and)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(\bconcat\s*\(|\bunion\s+select|\bgroup\s+by|\bhaving\b)",
    ]
    
    @classmethod
    def is_suspicious(cls, input_string: str) -> bool:
        """Check if input contains SQL injection patterns."""
        if not input_string:
            return False
        
        input_lower = input_string.lower()
        
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {input_string[:100]}")
                return True
        
        return False

class XSSProtection:
    """Cross-site scripting protection."""
    
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    @classmethod
    def is_suspicious(cls, input_string: str) -> bool:
        """Check if input contains XSS patterns."""
        if not input_string:
            return False
        
        input_lower = input_string.lower()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"Potential XSS detected: {input_string[:100]}")
                return True
        
        return False

class SecurityScanner:
    """Comprehensive security scanner for requests."""
    
    def __init__(self):
        self.sql_detector = SQLInjectionDetector()
        self.xss_protection = XSSProtection()
        self.validator = InputValidator()
    
    def scan_request(self, request: Request) -> Dict[str, Any]:
        """Scan request for security threats."""
        threats = []
        
        # Check query parameters
        for key, value in request.query_params.items():
            if self.sql_detector.is_suspicious(value):
                threats.append(f"SQL injection in query param: {key}")
            
            if self.xss_protection.is_suspicious(value):
                threats.append(f"XSS in query param: {key}")
        
        # Check path parameters
        if self.sql_detector.is_suspicious(str(request.url.path)):
            threats.append("SQL injection in path")
        
        if self.xss_protection.is_suspicious(str(request.url.path)):
            threats.append("XSS in path")
        
        # Check headers for suspicious content
        suspicious_headers = ["User-Agent", "Referer", "X-Forwarded-For"]
        for header in suspicious_headers:
            value = request.headers.get(header, "")
            if self.xss_protection.is_suspicious(value):
                threats.append(f"XSS in header: {header}")
        
        return {
            "threats_detected": len(threats) > 0,
            "threat_count": len(threats),
            "threats": threats,
            "risk_level": self.calculate_risk_level(threats)
        }
    
    def calculate_risk_level(self, threats: List[str]) -> str:
        """Calculate risk level based on threats."""
        if not threats:
            return "none"
        elif len(threats) <= 2:
            return "low"
        elif len(threats) <= 5:
            return "medium"
        else:
            return "high"

# Global security scanner
security_scanner = SecurityScanner()

def require_security_scan(func):
    """Decorator to require security scanning for endpoints."""
    async def wrapper(request: Request, *args, **kwargs):
        scan_result = security_scanner.scan_request(request)
        
        if scan_result["threats_detected"]:
            if scan_result["risk_level"] in ["medium", "high"]:
                logger.error(f"High-risk security threat detected: {scan_result}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request blocked due to security concerns"
                )
            else:
                logger.warning(f"Low-risk security threat detected: {scan_result}")
        
        return await func(request, *args, **kwargs)
    
    return wrapper

class CSRFProtection:
    """Cross-Site Request Forgery protection."""
    
    @staticmethod
    def generate_token() -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_token(token: str, expected_token: str) -> bool:
        """Verify CSRF token."""
        return secrets.compare_digest(token, expected_token)
    
    @staticmethod
    def get_token_from_request(request: Request) -> Optional[str]:
        """Extract CSRF token from request."""
        # Check header first
        token = request.headers.get("X-CSRF-Token")
        if token:
            return token
        
        # Check form data
        if hasattr(request, "form"):
            form_data = request.form()
            return form_data.get("csrf_token")
        
        return None

# Security utility functions
def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging."""
    return hashlib.sha256(data.encode()).hexdigest()[:12]

def generate_secure_filename(original_filename: str) -> str:
    """Generate secure filename."""
    # Remove path components
    filename = os.path.basename(original_filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Add timestamp prefix
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    return f"{timestamp}_{filename}"

def is_safe_redirect_url(url: str, allowed_hosts: List[str]) -> bool:
    """Check if redirect URL is safe."""
    try:
        parsed = urlparse(url)
        
        # Allow relative URLs
        if not parsed.netloc:
            return True
        
        # Check if host is in allowed list
        return parsed.netloc in allowed_hosts
        
    except Exception:
        return False 