# models/lab_results.py
# Add this to your existing models or create new file

from sqlalchemy import Column, Integer, String, Date, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class LabResult(Base):
    __tablename__ = "lab_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Test metadata
    test_type = Column(String, nullable=False)  # "Blood Panel", "Lipid Panel", etc.
    test_date = Column(Date, nullable=False)
    provider = Column(String, nullable=False)   # "Kaiser Permanente", "LabCorp", etc.
    
    # File storage
    original_file_path = Column(String)  # Path to uploaded file
    
    # Extracted results (stored as JSON)
    # Example: [{"name": "Glucose", "value": "95", "unit": "mg/dL", "reference_range": "70-100"}]
    results = Column(JSON)
    
    # AI extraction metadata
    extraction_confidence = Column(Float, default=0.0)  # 0.0 - 1.0
    manually_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user
    user = relationship("User", back_populates="lab_results")

# Add this to your User model:
# lab_results = relationship("LabResult", back_populates="user")
