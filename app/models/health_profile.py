"""
Health Profile Model
"""
from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    # Medical History
    current_conditions = Column(JSONB, default=list)
    medications = Column(JSONB, default=list)
    allergies = Column(JSONB, default=list)
    past_diagnoses = Column(JSONB, default=list)
    surgeries = Column(JSONB, default=list)
    family_history = Column(JSONB, default=dict)
    
    # Constitutional Types
    ayurvedic_dosha = Column(String(50))  # vata, pitta, kapha, combinations
    tcm_pattern = Column(String(100))
    body_type = Column(String(50))
    
    # Lifestyle
    diet_type = Column(String(50))  # vegetarian, vegan, omnivore, etc.
    exercise_frequency = Column(String(50))
    exercise_types = Column(JSONB, default=list)
    sleep_hours = Column(Numeric(3, 1))
    stress_level = Column(Integer)  # 1-10 scale
    occupation = Column(String(100))
    
    # Preferences
    preferred_traditions = Column(JSONB, default=list)
    treatment_philosophy = Column(Text)
    health_goals = Column(JSONB, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="health_profile")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "current_conditions": self.current_conditions or [],
            "medications": self.medications or [],
            "allergies": self.allergies or [],
            "past_diagnoses": self.past_diagnoses or [],
            "surgeries": self.surgeries or [],
            "family_history": self.family_history or {},
            "ayurvedic_dosha": self.ayurvedic_dosha,
            "tcm_pattern": self.tcm_pattern,
            "body_type": self.body_type,
            "diet_type": self.diet_type,
            "exercise_frequency": self.exercise_frequency,
            "exercise_types": self.exercise_types or [],
            "sleep_hours": float(self.sleep_hours) if self.sleep_hours else None,
            "stress_level": self.stress_level,
            "occupation": self.occupation,
            "preferred_traditions": self.preferred_traditions or [],
            "treatment_philosophy": self.treatment_philosophy,
            "health_goals": self.health_goals or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
