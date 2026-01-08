"""
Health Profile Model - With Family Member Support
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class HealthProfile(Base):
    """Health profile model for storing user health data"""
    __tablename__ = "health_profiles"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey('family_members.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Medical History
    current_conditions = Column(JSON, default=list)
    medications = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    past_diagnoses = Column(JSON, default=list)
    surgeries = Column(JSON, default=list)
    family_history = Column(JSON, default=dict)
    
    # Constitutional Types
    ayurvedic_dosha = Column(String(50), nullable=True)
    tcm_pattern = Column(String(100), nullable=True)
    body_type = Column(String(50), nullable=True)
    
    # Lifestyle
    diet_type = Column(String(50), nullable=True)
    exercise_frequency = Column(String(50), nullable=True)
    exercise_types = Column(JSON, default=list)
    sleep_hours = Column(Integer, nullable=True)
    stress_level = Column(Integer, nullable=True)
    occupation = Column(String(100), nullable=True)
    
    # Preferences
    preferred_traditions = Column(JSON, default=list)
    treatment_philosophy = Column(Text, nullable=True)
    health_goals = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="health_profiles")
    family_member = relationship("FamilyMember", back_populates="health_profiles")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "family_member_id": self.family_member_id,
            "current_conditions": self.current_conditions,
            "medications": self.medications,
            "allergies": self.allergies,
            "ayurvedic_dosha": self.ayurvedic_dosha,
            "tcm_pattern": self.tcm_pattern,
            "diet_type": self.diet_type,
            "exercise_frequency": self.exercise_frequency,
            "sleep_hours": self.sleep_hours,
            "stress_level": self.stress_level,
            "preferred_traditions": self.preferred_traditions,
            "health_goals": self.health_goals
        }
    
    def __repr__(self):
        return f"<HealthProfile user_id={self.user_id}>"
