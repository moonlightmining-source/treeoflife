"""
Treatment Model
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Treatment(Base):
    __tablename__ = "treatments"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Treatment details
    treatment_name = Column(String(255), nullable=False)
    treatment_type = Column(String(50))  # herb, supplement, food, exercise, practice, etc.
    tradition = Column(String(50))  # ayurveda, tcm, western, herbal, etc.
    dosage = Column(String(255))
    frequency = Column(String(100))
    
    # Timing
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    is_active = Column(Boolean, default=True, index=True)
    
    # Additional info
    purpose = Column(Text)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="treatments")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "treatment_name": self.treatment_name,
            "treatment_type": self.treatment_type,
            "tradition": self.tradition,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "is_active": self.is_active,
            "purpose": self.purpose,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
