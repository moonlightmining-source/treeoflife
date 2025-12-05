"""
Symptom Model
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Symptom(Base):
    __tablename__ = "symptoms"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Symptom details
    symptom_name = Column(String(255), nullable=False)
    severity = Column(Integer)  # 1-10 scale
    description = Column(Text)
    body_location = Column(String(100))
    
    # Timing
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_hours = Column(Integer)
    frequency = Column(String(50))  # constant, intermittent, occasional
    
    # Related info
    triggers = Column(JSONB, default=list)
    relieving_factors = Column(JSONB, default=list)
    associated_symptoms = Column(JSONB, default=list)
    
    # Timestamps
    logged_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="symptoms")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "symptom_name": self.symptom_name,
            "severity": self.severity,
            "description": self.description,
            "body_location": self.body_location,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_hours": self.duration_hours,
            "frequency": self.frequency,
            "triggers": self.triggers or [],
            "relieving_factors": self.relieving_factors or [],
            "associated_symptoms": self.associated_symptoms or [],
            "logged_at": self.logged_at.isoformat() if self.logged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
