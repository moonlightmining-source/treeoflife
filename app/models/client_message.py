"""
Client Message Model
Stores messages, images, and compliance data submitted by clients via portal
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class ClientMessage(Base):
    """
    Messages submitted by clients through their portal link
    
    Includes:
    - Text messages
    - Image uploads (stored as URLs)
    - Compliance checkbox data (stored as JSON)
    - Read/unread tracking
    """
    __tablename__ = "client_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    family_member_id = Column(Integer, ForeignKey('family_members.id', ondelete='CASCADE'), nullable=False)
    
    # Message content
    message_text = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # Compliance data stored as JSON
    # Example: {"took_supplements": true, "did_exercises": false, "followed_diet": true}
    compliance_data = Column(JSON, nullable=True)
    
    # Tracking
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime, nullable=True)  # NULL = unread
    
    # Relationships
    family_member = relationship("FamilyMember", back_populates="client_messages")
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "family_member_id": self.family_member_id,
            "message_text": self.message_text,
            "image_url": self.image_url,
            "compliance_data": self.compliance_data,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_unread": self.read_at is None
        }
