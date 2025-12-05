"""
User Model
"""
from sqlalchemy import Column, String, Boolean, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Personal info
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    sex = Column(String(20))
    location = Column(String(255))
    phone = Column(String(20))
    profile_image_url = Column(String)
    
    # Subscription
    subscription_tier = Column(String(20), default="free")  # free, premium, pro
    subscription_status = Column(String(20), default="active")
    subscription_expires_at = Column(DateTime)
    
    # Account status
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Relationships
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user")
    symptoms = relationship("Symptom", back_populates="user")
    treatments = relationship("Treatment", back_populates="user")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "sex": self.sex,
            "location": self.location,
            "phone": self.phone,
            "profile_image_url": self.profile_image_url,
            "subscription_tier": self.subscription_tier,
            "subscription_status": self.subscription_status,
            "email_verified": self.email_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
