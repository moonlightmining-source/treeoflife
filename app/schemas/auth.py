"""
Authentication Schemas
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    terms_accepted: bool
    
    @validator('password')
    def password_strength(cls, v):
        """Validate password strength"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v
    
    @validator('terms_accepted')
    def terms_must_be_accepted(cls, v):
        """Validate terms are accepted"""
        if not v:
            raise ValueError('Terms of service must be accepted')
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User data response"""
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    subscription_tier: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Token data"""
    access_token: str
    token_type: str
    user: UserResponse


class TokenResponse(BaseModel):
    """Token response wrapper"""
    success: bool = True
    data: TokenData


class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)
