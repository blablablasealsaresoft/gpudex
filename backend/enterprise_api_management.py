# Enterprise API Management System for GPUDex
# Comprehensive API key management, billing, teams, and security

import os
import time
import hashlib
import secrets
import logging
import json
import uuid
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from functools import wraps

from fastapi import HTTPException, Request, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
import jwt
import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database import DatabaseManager

logger = logging.getLogger(__name__)

class APIKeyScope(str, Enum):
    """API Key permission scopes"""
    READ_PRICES = "read:prices"
    READ_ANALYTICS = "read:analytics" 
    CREATE_RENTALS = "create:rentals"
    MANAGE_RENTALS = "manage:rentals"
    READ_PREDICTIONS = "read:predictions"
    ADMIN = "admin:*"
    BILLING = "billing:*"

class PlanType(str, Enum):
    """Subscription plan types"""
    FREE = "free"
    STARTER = "starter" 
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class UsageMetric(str, Enum):
    """Billable usage metrics"""
    API_REQUESTS = "api_requests"
    GPU_HOURS = "gpu_hours"
    DATA_TRANSFER = "data_transfer"
    PREDICTIONS = "predictions"

@dataclass
class PlanLimits:
    """Plan limits and features"""
    requests_per_hour: int
    requests_per_day: int
    requests_per_month: int
    max_team_members: int
    max_api_keys: int
    scopes: List[APIKeyScope]
    price_usd: float
    gpu_hour_credits: int
    support_level: str

# Plan configurations
PLAN_LIMITS = {
    PlanType.FREE: PlanLimits(
        requests_per_hour=100,
        requests_per_day=1000,
        requests_per_month=10000,
        max_team_members=1,
        max_api_keys=3,
        scopes=[APIKeyScope.READ_PRICES],
        price_usd=0,
        gpu_hour_credits=0,
        support_level="community"
    ),
    PlanType.STARTER: PlanLimits(
        requests_per_hour=1000,
        requests_per_day=10000,
        requests_per_month=100000,
        max_team_members=5,
        max_api_keys=10,
        scopes=[APIKeyScope.READ_PRICES, APIKeyScope.READ_ANALYTICS, APIKeyScope.CREATE_RENTALS],
        price_usd=29,
        gpu_hour_credits=50,
        support_level="email"
    ),
    PlanType.PRO: PlanLimits(
        requests_per_hour=5000,
        requests_per_day=50000,
        requests_per_month=500000,
        max_team_members=15,
        max_api_keys=25,
        scopes=[APIKeyScope.READ_PRICES, APIKeyScope.READ_ANALYTICS, APIKeyScope.CREATE_RENTALS, 
                APIKeyScope.MANAGE_RENTALS, APIKeyScope.READ_PREDICTIONS],
        price_usd=99,
        gpu_hour_credits=200,
        support_level="priority"
    ),
    PlanType.ENTERPRISE: PlanLimits(
        requests_per_hour=20000,
        requests_per_day=200000,
        requests_per_month=2000000,
        max_team_members=100,
        max_api_keys=100,
        scopes=list(APIKeyScope),
        price_usd=499,
        gpu_hour_credits=1000,
        support_level="dedicated"
    )
}

class APIKeyRequest(BaseModel):
    """Request model for creating API keys"""
    name: str
    scopes: List[APIKeyScope]
    expires_at: Optional[datetime] = None
    ip_whitelist: Optional[List[str]] = None
    rate_limit_override: Optional[Dict[str, int]] = None

class TeamInviteRequest(BaseModel):
    """Request model for team invitations"""
    email: EmailStr
    role: str = "member"
    scopes: List[APIKeyScope] = []

class UsageAnalytics(BaseModel):
    """Usage analytics response"""
    period: str
    total_requests: int
    successful_requests: int
    error_requests: int
    top_endpoints: List[Dict]
    usage_by_day: List[Dict]
    cost_breakdown: Dict[str, float]

class EnterpriseAPIManager:
    """Enterprise-grade API key and billing management"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key")
        self.jwt_algorithm = "HS256"
        
    def generate_api_key(self, prefix: str = "gpudx") -> str:
        """Generate a secure API key with entropy"""
        random_bytes = secrets.token_bytes(32)
        key_hash = hashlib.sha256(random_bytes).hexdigest()
        return f"{prefix}_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(32))}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_organization(self, name: str, owner_email: str, plan: PlanType = PlanType.FREE) -> Dict:
        """Create a new organization"""
        try:
            db_manager = DatabaseManager()
            org_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO organizations (id, name, owner_email, plan_type, created_at, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING *
            """
            
            result = db_manager.db.execute(query, (org_id, name, owner_email, plan.value))
            row = result.fetchone()
            db_manager.db.commit()
            
            # Create default team member entry
            await self.add_team_member(org_id, owner_email, "owner", list(APIKeyScope))
            
            db_manager.close()
            
            return {
                "organization_id": org_id,
                "name": name,
                "owner_email": owner_email,
                "plan": plan.value,
                "created_at": row[4] if row else datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            raise HTTPException(status_code=500, detail="Failed to create organization")
    
    async def create_api_key(self, org_id: str, user_email: str, request: APIKeyRequest) -> Dict:
        """Create a new API key with scopes and permissions"""
        try:
            db_manager = DatabaseManager()
            
            # Check organization limits
            org_info = await self.get_organization(org_id)
            plan_limits = PLAN_LIMITS[PlanType(org_info["plan_type"])]
            
            # Count existing API keys
            count_query = "SELECT COUNT(*) FROM api_keys WHERE organization_id = %s AND is_active = true"
            result = db_manager.db.execute(count_query, (org_id,))
            key_count = result.fetchone()[0]
            
            if key_count >= plan_limits.max_api_keys:
                raise HTTPException(
                    status_code=403, 
                    detail=f"API key limit reached ({plan_limits.max_api_keys}). Upgrade your plan."
                )
            
            # Validate scopes against plan
            for scope in request.scopes:
                if scope not in plan_limits.scopes and APIKeyScope.ADMIN not in plan_limits.scopes:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Scope '{scope}' not available in {org_info['plan_type']} plan"
                    )
            
            # Generate API key
            api_key = self.generate_api_key()
            key_hash = self.hash_api_key(api_key)
            key_id = str(uuid.uuid4())
            
            # Insert API key
            insert_query = """
                INSERT INTO api_keys_v2 (
                    id, organization_id, name, key_hash, scopes, created_by,
                    expires_at, ip_whitelist, rate_limit_override, is_active,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING created_at
            """
            
            result = db_manager.db.execute(insert_query, (
                key_id, org_id, request.name, key_hash, 
                json.dumps([s.value for s in request.scopes]),
                user_email, request.expires_at,
                json.dumps(request.ip_whitelist) if request.ip_whitelist else None,
                json.dumps(request.rate_limit_override) if request.rate_limit_override else None
            ))
            
            created_at = result.fetchone()[0]
            db_manager.db.commit()
            db_manager.close()
            
            return {
                "api_key": api_key,  # Only returned once!
                "key_id": key_id,
                "name": request.name,
                "scopes": [s.value for s in request.scopes],
                "created_at": created_at,
                "expires_at": request.expires_at,
                "organization_id": org_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            raise HTTPException(status_code=500, detail="Failed to create API key")
    
    async def validate_api_key(self, api_key: str, required_scope: Optional[APIKeyScope] = None, 
                             request_ip: Optional[str] = None) -> Optional[Dict]:
        """Validate API key with scope and IP checking"""
        try:
            db_manager = DatabaseManager()
            key_hash = self.hash_api_key(api_key)
            
            query = """
                SELECT ak.id, ak.organization_id, ak.name, ak.scopes, ak.created_by,
                       ak.expires_at, ak.ip_whitelist, ak.rate_limit_override,
                       ak.last_used_at, ak.usage_count, ak.is_active,
                       o.plan_type, o.name as org_name
                FROM api_keys_v2 ak
                JOIN organizations o ON ak.organization_id = o.id
                WHERE ak.key_hash = %s AND ak.is_active = true
            """
            
            result = db_manager.db.execute(query, (key_hash,))
            row = result.fetchone()
            db_manager.close()
            
            if not row:
                return None
            
            # Check expiration
            if row[5] and datetime.now() > row[5]:  # expires_at
                return None
            
            # Parse scopes
            scopes = json.loads(row[3]) if row[3] else []
            
            # Check required scope
            if required_scope and required_scope.value not in scopes and APIKeyScope.ADMIN.value not in scopes:
                return None
            
            # Check IP whitelist
            ip_whitelist = json.loads(row[6]) if row[6] else None
            if ip_whitelist and request_ip and request_ip not in ip_whitelist:
                return None
            
            return {
                "key_id": row[0],
                "organization_id": row[1],
                "name": row[2],
                "scopes": scopes,
                "created_by": row[4],
                "expires_at": row[5],
                "ip_whitelist": ip_whitelist,
                "rate_limit_override": json.loads(row[7]) if row[7] else None,
                "last_used_at": row[8],
                "usage_count": row[9],
                "plan_type": row[11],
                "organization_name": row[12]
            }
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None
    
    async def record_usage(self, key_info: Dict, endpoint: str, status_code: int, 
                          response_time: float, request_size: int = 0, response_size: int = 0):
        """Record detailed API usage for billing and analytics"""
        try:
            db_manager = DatabaseManager()
            
            # Update API key last used
            update_key_query = """
                UPDATE api_keys_v2 
                SET last_used_at = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                WHERE id = %s
            """
            db_manager.db.execute(update_key_query, (key_info["key_id"],))
            
            # Record detailed usage
            usage_query = """
                INSERT INTO api_usage_logs (
                    organization_id, api_key_id, endpoint, method, status_code,
                    response_time_ms, request_size_bytes, response_size_bytes,
                    timestamp, billing_units
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            """
            
            # Calculate billing units (1 unit per request for now)
            billing_units = 1
            if "gpu" in endpoint.lower() or "rental" in endpoint.lower():
                billing_units = 2  # Premium endpoints cost more
            
            db_manager.db.execute(usage_query, (
                key_info["organization_id"], key_info["key_id"], endpoint, "GET",
                status_code, response_time * 1000, request_size, response_size, billing_units
            ))
            
            db_manager.db.commit()
            db_manager.close()
            
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
    
    async def get_usage_analytics(self, org_id: str, period: str = "30d") -> UsageAnalytics:
        """Get comprehensive usage analytics"""
        try:
            db_manager = DatabaseManager()
            
            # Determine date range
            if period == "24h":
                since = datetime.now() - timedelta(hours=24)
            elif period == "7d":
                since = datetime.now() - timedelta(days=7)
            elif period == "30d":
                since = datetime.now() - timedelta(days=30)
            else:
                since = datetime.now() - timedelta(days=30)
            
            # Total requests
            total_query = """
                SELECT COUNT(*), 
                       COUNT(CASE WHEN status_code < 400 THEN 1 END) as successful,
                       COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors
                FROM api_usage_logs 
                WHERE organization_id = %s AND timestamp >= %s
            """
            result = db_manager.db.execute(total_query, (org_id, since))
            total_row = result.fetchone()
            
            # Top endpoints
            endpoints_query = """
                SELECT endpoint, COUNT(*) as count
                FROM api_usage_logs 
                WHERE organization_id = %s AND timestamp >= %s
                GROUP BY endpoint
                ORDER BY count DESC
                LIMIT 10
            """
            result = db_manager.db.execute(endpoints_query, (org_id, since))
            top_endpoints = [{"endpoint": row[0], "count": row[1]} for row in result.fetchall()]
            
            # Usage by day
            daily_query = """
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM api_usage_logs 
                WHERE organization_id = %s AND timestamp >= %s
                GROUP BY DATE(timestamp)
                ORDER BY date
            """
            result = db_manager.db.execute(daily_query, (org_id, since))
            usage_by_day = [{"date": str(row[0]), "requests": row[1]} for row in result.fetchall()]
            
            # Cost breakdown (simplified)
            total_units_query = """
                SELECT SUM(billing_units) FROM api_usage_logs 
                WHERE organization_id = %s AND timestamp >= %s
            """
            result = db_manager.db.execute(total_units_query, (org_id, since))
            total_units = result.fetchone()[0] or 0
            
            cost_per_unit = 0.001  # $0.001 per API unit
            api_cost = total_units * cost_per_unit
            
            db_manager.close()
            
            return UsageAnalytics(
                period=period,
                total_requests=total_row[0] or 0,
                successful_requests=total_row[1] or 0,
                error_requests=total_row[2] or 0,
                top_endpoints=top_endpoints,
                usage_by_day=usage_by_day,
                cost_breakdown={
                    "api_requests": api_cost,
                    "gpu_hours": 0,  # TODO: Calculate from rental records
                    "total": api_cost
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            raise HTTPException(status_code=500, detail="Failed to get usage analytics")
    
    async def rotate_api_key(self, key_id: str, org_id: str) -> Dict:
        """Rotate an API key (generate new key, invalidate old)"""
        try:
            db_manager = DatabaseManager()
            
            # Get existing key info
            get_query = """
                SELECT name, scopes, expires_at, ip_whitelist, rate_limit_override, created_by
                FROM api_keys_v2 
                WHERE id = %s AND organization_id = %s AND is_active = true
            """
            result = db_manager.db.execute(get_query, (key_id, org_id))
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="API key not found")
            
            # Generate new key
            new_api_key = self.generate_api_key()
            new_key_hash = self.hash_api_key(new_api_key)
            new_key_id = str(uuid.uuid4())
            
            # Deactivate old key
            deactivate_query = """
                UPDATE api_keys_v2 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            db_manager.db.execute(deactivate_query, (key_id,))
            
            # Create new key
            create_query = """
                INSERT INTO api_keys_v2 (
                    id, organization_id, name, key_hash, scopes, created_by,
                    expires_at, ip_whitelist, rate_limit_override, is_active,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            
            db_manager.db.execute(create_query, (
                new_key_id, org_id, f"{row[0]} (rotated)", new_key_hash,
                row[1], row[5], row[2], row[3], row[4]
            ))
            
            db_manager.db.commit()
            db_manager.close()
            
            return {
                "new_api_key": new_api_key,
                "new_key_id": new_key_id,
                "rotated_at": datetime.now(),
                "old_key_id": key_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error rotating API key: {e}")
            raise HTTPException(status_code=500, detail="Failed to rotate API key")
    
    async def get_organization(self, org_id: str) -> Dict:
        """Get organization details"""
        try:
            db_manager = DatabaseManager()
            
            query = """
                SELECT id, name, owner_email, plan_type, created_at, updated_at
                FROM organizations 
                WHERE id = %s
            """
            
            result = db_manager.db.execute(query, (org_id,))
            row = result.fetchone()
            db_manager.close()
            
            if not row:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            return {
                "id": row[0],
                "name": row[1],
                "owner_email": row[2], 
                "plan_type": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting organization: {e}")
            raise HTTPException(status_code=500, detail="Failed to get organization")
    
    async def add_team_member(self, org_id: str, email: str, role: str, scopes: List[APIKeyScope]):
        """Add a team member to organization"""
        try:
            db_manager = DatabaseManager()
            
            query = """
                INSERT INTO team_members (organization_id, email, role, scopes, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (organization_id, email) 
                DO UPDATE SET role = EXCLUDED.role, scopes = EXCLUDED.scopes
            """
            
            db_manager.db.execute(query, (
                org_id, email, role, json.dumps([s.value for s in scopes])
            ))
            db_manager.db.commit()
            db_manager.close()
            
        except Exception as e:
            logger.error(f"Error adding team member: {e}")
            raise HTTPException(status_code=500, detail="Failed to add team member")

# Global instance
enterprise_api_manager = EnterpriseAPIManager()

# Enhanced dependency functions
async def get_api_key_info_v2(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(enterprise_api_manager.security)
) -> Optional[Dict]:
    """Enhanced API key validation with IP checking"""
    if not credentials:
        return None
    
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    api_key_info = await enterprise_api_manager.validate_api_key(
        credentials.credentials, 
        request_ip=client_ip
    )
    
    if api_key_info:
        # Record usage in background
        endpoint = str(request.url.path)
        # Note: response time and sizes would be calculated in middleware
        await enterprise_api_manager.record_usage(
            api_key_info, endpoint, 200, 0.1  # Defaults for now
        )
    
    return api_key_info

def require_scope(scope: APIKeyScope):
    """Dependency factory for requiring specific scopes"""
    async def check_scope(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(enterprise_api_manager.security)
    ) -> Dict:
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        client_ip = request.client.host
        api_key_info = await enterprise_api_manager.validate_api_key(
            credentials.credentials, scope, client_ip
        )
        
        if not api_key_info:
            raise HTTPException(
                status_code=403,
                detail=f"API key lacks required scope: {scope.value}"
            )
        
        return api_key_info
    
    return check_scope

# Rate limiting with plan awareness
class EnterpriseRateLimiter:
    """Enterprise rate limiter with plan-based limits"""
    
    def __init__(self):
        self.usage_cache = {}
        
    async def check_limits(self, api_key_info: Dict) -> Tuple[bool, Dict]:
        """Check rate limits based on plan"""
        plan_type = PlanType(api_key_info["plan_type"])
        limits = PLAN_LIMITS[plan_type]
        
        # Check overrides
        if api_key_info.get("rate_limit_override"):
            overrides = api_key_info["rate_limit_override"]
            limits.requests_per_hour = overrides.get("hourly", limits.requests_per_hour)
            limits.requests_per_day = overrides.get("daily", limits.requests_per_day)
        
        org_id = api_key_info["organization_id"]
        current_time = time.time()
        
        # Check hourly limit
        hour_key = f"{org_id}:hour:{int(current_time // 3600)}"
        hour_usage = self.usage_cache.get(hour_key, 0)
        
        if hour_usage >= limits.requests_per_hour:
            return False, {
                "error": "Hourly rate limit exceeded",
                "limit": limits.requests_per_hour,
                "used": hour_usage,
                "plan": plan_type.value
            }
        
        # Increment usage
        self.usage_cache[hour_key] = hour_usage + 1
        
        return True, {
            "hourly_usage": hour_usage + 1,
            "hourly_limit": limits.requests_per_hour,
            "plan": plan_type.value
        }

enterprise_rate_limiter = EnterpriseRateLimiter() 