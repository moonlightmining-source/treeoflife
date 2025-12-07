"""
Authentication Schemas
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegister(BaseModel):
    """User registration schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date = Field(..., description="Format: YYYY-MM-DD (e.g., 1990-05-15)")
    sex: str = Field(..., description="male, female, other")
    location: str = Field(..., description="5-digit ZIP code (e.g., 94102)")
    terms_accepted: bool = Field(..., description="Must accept terms of service")
    
    @field_validator('location')
    @classmethod
    def validate_zip(cls, v: str) -> str:
        """Validate ZIP code format"""
        # Remove any spaces or dashes
        zip_code = v.strip().replace('-', '').replace(' ', '')
        
        # Check if it's a 5-digit number
        if not re.match(r'^\d{5}$', zip_code):
            raise ValueError('ZIP code must be 5 digits (e.g., 94102)')
        
        return zip_code
    
    @field_validator('sex')
    @classmethod
    def validate_sex(cls, v: str) -> str:
        """Validate sex field"""
        allowed = ['male', 'female', 'other']
        if v.lower() not in allowed:
            raise ValueError(f'Sex must be one of: {", ".join(allowed)}')
        return v.lower()
    
    @field_validator('terms_accepted')
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        """Validate terms acceptance"""
        if not v:
            raise ValueError('You must accept the terms of service to register')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "moonlight_mining@yahoo.com",
                "password": "Pootchi30",
                "first_name": "Robert",
                "last_name": "Poat",
                "date_of_birth": "1964-05-10",
                "sex": "male",
                "location": "94583",
                "terms_accepted": True
            }
        }


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "moonlight_mining@yahoo.com",
                "password": "Pootchi30"
            }
        }


class UserResponse(BaseModel):
    """User response schema"""
    id: str
    email: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str
    location: str
    subscription_tier: str
    subscription_status: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordReset(BaseModel):
    """Password reset request schema"""
    email: EmailStr
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "moonlight_mining@yahoo.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset-token-here",
                "new_password": "NewSecurePass123!"
            }
        }
