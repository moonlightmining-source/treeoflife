"""
Treatment Model - Simplified (No Relationships)
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Treatment(Base):
    """Treatment tracking model"""
    __tablename__ = "treatments"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Treatment details
    treatment_name = Column(String(255), nullable=False)
    treatment_type = Column(String(50), nullable=True)
    tradition = Column(String(50), nullable=True)
    dosage = Column(String(255), nullable=True)
    frequency = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    purpose = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
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
            "is_active": self.is_active,
            "purpose": self.purpose,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
