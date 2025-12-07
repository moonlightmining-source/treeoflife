"""
Authentication Routes
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, UserResponse, TokenResponse, PasswordReset
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user
    
    - Creates user account
    - Returns JWT token for immediate login
    """
    logger.info(f"Registration attempt for email: {user_data.email}")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Registration failed: Email already registered - {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user (WITHOUT phone field)
    try:
        new_user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            date_of_birth=user_data.date_of_birth,
            sex=user_data.sex,
            location=user_data.location,
            # phone field removed
            subscription_tier="free",
            subscription_status="active",
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"✅ User registered successfully: {new_user.email} (ID: {new_user.id})")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(new_user)
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password
    
    - Returns JWT token for authentication
    """
    logger.info(f"Login attempt for email: {credentials.email}")
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        logger.warning(f"Login failed: User not found - {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Login failed: Invalid password - {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login failed: Account inactive - {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"✅ User logged in successfully: {user.email}")
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_db)):
    """
    Get current user information
    
    - Requires authentication
    - Returns user profile
    """
    return UserResponse.model_validate(current_user)


@router.post("/auth/password-reset")
async def request_password_reset(data: PasswordReset, db: Session = Depends(get_db)):
    """
    Request password reset
    
    - Sends reset email (not implemented yet)
    """
    # TODO: Implement email sending
    logger.info(f"Password reset requested for: {data.email}")
    
    return {
        "message": "If the email exists, a password reset link has been sent"
    }
