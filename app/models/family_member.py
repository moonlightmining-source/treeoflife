"""
Family Member Model
Stores family members for Basic/Premium/Pro tier users
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class FamilyMember(Base):
    """
    Family member model for multi-user accounts
    
    Subscription tier limits:
    - Free: 0 family members
    - Basic: 1 family member
    - Premium: 5 family members
    - Pro: 10 family members (clients)
    """
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Personal information
    name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    sex = Column(String(20), nullable=True)
    relationship = Column(String(50), nullable=True)  # e.g., "spouse", "child", "parent"
    
    # Contact (optional)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Health tracking
    notes = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="family_members")
    health_profiles = relationship("HealthProfile", back_populates="family_member", cascade="all, delete-orphan")
    client_messages = relationship("ClientMessage", back_populates="family_member", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "name": self.name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "sex": self.sex,
            "relationship": self.relationship,
            "email": self.email,
            "phone": self.phone,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<FamilyMember {self.name}>"
