"""
Symptom Model - Simplified (No Relationships)
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Symptom(Base):
    """Symptom tracking model"""
    __tablename__ = "symptoms"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Symptom details
    symptom_name = Column(String(255), nullable=False)
    severity = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    body_location = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_hours = Column(Integer, nullable=True)
    frequency = Column(String(50), nullable=True)
    triggers = Column(JSON, default=list)
    relieving_factors = Column(JSON, default=list)
    associated_symptoms = Column(JSON, default=list)
    
    # Timestamps
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
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
            "logged_at": self.logged_at.isoformat() if self.logged_at else None
        }
