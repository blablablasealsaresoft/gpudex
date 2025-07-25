"""
GPUDex Authentication Service
Comprehensive user authentication with JWT, security features, and user management.
"""

import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    subscription_tier = Column(String(50), default="free")  # free, basic, premium, enterprise
    api_limit_daily = Column(Integer, default=100)
    api_calls_today = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True))
    reset_token = Column(String(255))
    verification_token = Column(String(255))

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    session_token = Column(String(255), unique=True, index=True)
    refresh_token = Column(String(255), unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# Pydantic models
class UserRegistration(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username must be between 3 and 50 characters')
        if not v.isalnum():
            raise ValueError('Username must contain only alphanumeric characters')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_verified: bool
    is_premium: bool
    subscription_tier: str
    api_limit_daily: int
    api_calls_today: int
    created_at: datetime
    last_login: Optional[datetime]

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile

class AuthService:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql://gpudex:gpudex123@localhost:5432/gpudex")
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 30
        
        # Initialize database
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        logger.info("Auth service initialized successfully")
    
    def get_db(self) -> Session:
        """Get database session"""
        db = self.SessionLocal()
        try:
            return db
        finally:
            pass  # Session will be closed by caller
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def generate_tokens(self, user_id: int, email: str) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        now = datetime.now(timezone.utc)
        
        # Access token payload
        access_payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire_minutes)
        }
        
        # Refresh token payload
        refresh_payload = {
            "sub": str(user_id),
            "email": email,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.refresh_token_expire_days)
        }
        
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != token_type:
                return None
            
            if datetime.fromtimestamp(payload["exp"], tz=timezone.utc) < datetime.now(timezone.utc):
                return None
            
            return payload
        except jwt.InvalidTokenError:
            return None
    
    def register_user(self, user_data: UserRegistration) -> UserProfile:
        """Register a new user"""
        db = self.get_db()
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.email == user_data.email) | (User.username == user_data.username)
            ).first()
            
            if existing_user:
                if existing_user.email == user_data.email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
            
            # Create new user
            hashed_password = self.hash_password(user_data.password)
            new_user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            return UserProfile(**new_user.__dict__)
        
        finally:
            db.close()
    
    def login_user(self, login_data: UserLogin, ip_address: str = None, user_agent: str = None) -> TokenResponse:
        """Authenticate user and create session"""
        db = self.get_db()
        try:
            # Get user by email
            user = db.query(User).filter(User.email == login_data.email).first()
            
            if not user or not self.verify_password(login_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is deactivated"
                )
            
            # Generate tokens
            tokens = self.generate_tokens(user.id, user.email)
            
            # Create session record
            session = UserSession(
                user_id=user.id,
                session_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_at=datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(session)
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            
            db.commit()
            
            return TokenResponse(
                **tokens,
                user=UserProfile(**user.__dict__)
            )
        
        finally:
            db.close()
    
    def create_session(self, user_id: int, access_token: str, refresh_token: str, 
                      ip_address: str = None, user_agent: str = None) -> UserSession:
        """Create a new user session"""
        db = self.get_db()
        try:
            session = UserSession(
                user_id=user_id,
                session_token=access_token,
                refresh_token=refresh_token,
                expires_at=datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            return session
        
        finally:
            db.close()
    
    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Generate new access token using refresh token"""
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        db = self.get_db()
        try:
            # Verify session exists and is active
            session = db.query(UserSession).filter(
                UserSession.refresh_token == refresh_token,
                UserSession.is_active == True
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session not found or inactive"
                )
            
            # Get user
            user = db.query(User).filter(User.id == session.user_id).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Generate new tokens
            tokens = self.generate_tokens(user.id, user.email)
            
            # Update session
            session.session_token = tokens["access_token"]
            session.expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
            
            db.commit()
            
            return TokenResponse(
                **tokens,
                user=UserProfile(**user.__dict__)
            )
        
        finally:
            db.close()
    
    def logout_user(self, access_token: str) -> bool:
        """Logout user and deactivate session"""
        payload = self.verify_token(access_token, "access")
        if not payload:
            return False
        
        db = self.get_db()
        try:
            session = db.query(UserSession).filter(
                UserSession.session_token == access_token,
                UserSession.is_active == True
            ).first()
            
            if session:
                session.is_active = False
                db.commit()
                return True
            
            return False
        
        finally:
            db.close()
    
    def get_current_user(self, access_token: str) -> Optional[UserProfile]:
        """Get current user from access token"""
        payload = self.verify_token(access_token, "access")
        if not payload:
            return None
        
        db = self.get_db()
        try:
            user = db.query(User).filter(User.id == int(payload["sub"])).first()
            if user and user.is_active:
                return UserProfile(**user.__dict__)
            return None
        
        finally:
            db.close()
    
    def update_user_profile(self, user_id: int, updates: Dict[str, Any]) -> UserProfile:
        """Update user profile"""
        db = self.get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update allowed fields
            allowed_fields = ["first_name", "last_name", "username"]
            for field, value in updates.items():
                if field in allowed_fields and hasattr(user, field):
                    setattr(user, field, value)
            
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            
            return UserProfile(**user.__dict__)
        
        finally:
            db.close()
    
    def change_password(self, user_id: int, password_change: PasswordChange) -> bool:
        """Change user password"""
        db = self.get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify current password
            if not self.verify_password(password_change.current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password
            user.hashed_password = self.hash_password(password_change.new_password)
            user.updated_at = datetime.now(timezone.utc)
            
            # Deactivate all sessions except current one
            db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).update({"is_active": False})
            
            db.commit()
            return True
        
        finally:
            db.close()

# Global auth service instance
auth_service = AuthService()

# FastAPI dependencies
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """FastAPI dependency to get current user"""
    user = auth_service.get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[UserProfile]:
    """FastAPI dependency to get current user (optional)"""
    if not credentials:
        return None
    return auth_service.get_current_user(credentials.credentials) 