from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database import Base

class ClientViewToken(Base):
    __tablename__ = "client_view_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    family_member_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    practitioner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    is_active = Column(Boolean, default=True)
