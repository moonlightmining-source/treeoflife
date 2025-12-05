"""
Chat Schemas
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Create new conversation request"""
    initial_message: str = Field(..., min_length=1, max_length=5000)
    title: Optional[str] = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    """Conversation response"""
    success: bool = True
    data: Dict[str, Any]


class MessageCreate(BaseModel):
    """Create new message request"""
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Message response"""
    success: bool = True
    data: Dict[str, Any]
