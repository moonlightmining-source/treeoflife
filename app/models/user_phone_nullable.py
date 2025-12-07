"""
User Model
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class User(Base):
    """User model for authentication and profile"""
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    sex = Column(String(20), nullable=False)
    location = Column(String(255), nullable=False)  # ZIP code
    phone = Column(String(20), nullable=True)  # ✅ Made nullable
    profile_image_url = Column(String(500), nullable=True)
    
    # Subscription
    subscription_tier = Column(String(20), default="free")  # free, premium, pro
    subscription_status = Column(String(20), default="active")  # active, cancelled, expired
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Account status
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "sex": self.sex,
            "location": self.location,
            "phone": self.phone,
            "subscription_tier": self.subscription_tier,
            "subscription_status": self.subscription_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active
        }
