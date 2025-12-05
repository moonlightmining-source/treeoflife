"""
Message Model
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Message(Base):
    __tablename__ = "messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Metadata - RENAMED from 'metadata' to avoid SQLAlchemy reserved word
    tokens_used = Column(Integer)
    model_used = Column(String(50))
    sources = Column(JSONB, default=list)  # Knowledge base sources cited
    message_metadata = Column(JSONB, default=dict)  # CHANGED: was 'metadata'
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "role": self.role,
            "content": self.content,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "sources": self.sources or [],
            "metadata": self.message_metadata or {},  # Return as 'metadata' in API
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
