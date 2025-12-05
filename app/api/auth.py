"""
Authentication API Routes
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    PasswordReset,
    PasswordResetConfirm
)
from app.utils.security import get_password_hash, verify_password
from app.config import settings


router = APIRouter()


def create_access_token(user_id: str) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access"
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        date_of_birth=user_data.date_of_birth,
        sex=user_data.sex,
        location=user_data.location,
        phone=user_data.phone
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(new_user.id)
    
    return TokenResponse(
        success=True,
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(
                id=str(new_user.id),
                email=new_user.email,
                first_name=new_user.first_name,
                last_name=new_user.last_name
            )
        }
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(user.id)
    
    return TokenResponse(
        success=True,
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(
                id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name
            )
        }
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user information
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        date_of_birth=current_user.date_of_birth,
        sex=current_user.sex,
        location=current_user.location,
        phone=current_user.phone,
        subscription_tier=current_user.subscription_tier,
        created_at=current_user.created_at
    )


@router.post("/auth/password-reset")
async def request_password_reset(data: PasswordReset, db: Session = Depends(get_db)):
    """
    Request password reset (sends email in production)
    """
    # Find user
    user = db.query(User).filter(User.email == data.email).first()
    
    # Always return success (don't reveal if email exists)
    return {
        "success": True,
        "message": "If the email exists, a password reset link has been sent"
    }


@router.post("/auth/password-reset/confirm")
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token
    """
    # In production, verify reset token
    # For now, simplified implementation
    
    return {
        "success": True,
        "message": "Password reset successful"
    }
