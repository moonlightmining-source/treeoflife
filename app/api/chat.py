"""
Chat API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse
)
from pydantic import BaseModel

class MessageCreateWithMember(BaseModel):
    content: str
    member_id: Optional[int] = None
    member_name: Optional[str] = None
from app.services.claude_service import claude_service


router = APIRouter()


@router.post("/chat/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation with initial message
    """
    # Create conversation
    conversation = Conversation(
        user_id=current_user.id,
        title=data.title or data.initial_message[:50] + "..." if len(data.initial_message) > 50 else data.initial_message
    )
    db.add(conversation)
    db.flush()
    
    # Create user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.initial_message
    )
    db.add(user_message)
    
    # Get AI response
    try:
       response = await claude_service.generate_response(
            user_message=data.initial_message,
            user_profile={},  # TODO: Get from health profile
            conversation_history=[],
            member_id=getattr(data, 'member_id', None),
            member_name=getattr(data, 'member_name', None)
        )
        
        # Create AI message
        ai_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response["content"],
            tokens_used=response.get("tokens_used"),
            model_used="claude-sonnet-4-20250514"
        )
        db.add(ai_message)
        
        # Update conversation
        conversation.last_message_at = ai_message.created_at
        conversation.emergency_detected = response.get("emergency", False)
        
        db.commit()
        db.refresh(conversation)
        
        return ConversationResponse(
            success=True,
            data={
                "conversation": conversation.to_dict(),
                "message": ai_message.to_dict()
            }
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI response: {str(e)}"
        )


@router.get("/chat/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for current user
    """
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.status == "active"
    ).order_by(Conversation.updated_at.desc()).all()
    
    return {
        "success": True,
        "data": [conv.to_dict() for conv in conversations]
    }


@router.get("/chat/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation with messages
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return {
        "success": True,
        "data": {
            "conversation": conversation.to_dict(),
            "messages": [msg.to_dict() for msg in messages]
        }
    }


@router.post("/chat/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    data: MessageCreateWithMember,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message in an existing conversation
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get conversation history
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]
    
    # Create user message
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=data.content
    )
    db.add(user_message)
    
    # Get AI response
    try:
        response = await claude_service.generate_response(
            user_message=data.content,
            user_profile={},  # TODO: Get from health profile
            conversation_history=conversation_history,
            member_id=data.member_id,
            member_name=data.member_name
        )
        
        # Create AI message
        ai_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=response["content"],
            tokens_used=response.get("tokens_used"),
            model_used="claude-sonnet-4-20250514"
        )
        db.add(ai_message)
        
        # Update conversation
        conversation.last_message_at = ai_message.created_at
        conversation.emergency_detected = response.get("emergency", False)
        
        db.commit()
        db.refresh(ai_message)
        
        return MessageResponse(
            success=True,
            data={
                "message": ai_message.to_dict(),
                "emergency_detected": response.get("emergency", False)
            }
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI response: {str(e)}"
        )


@router.delete("/chat/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete (archive) a conversation
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    conversation.status = "archived"
    db.commit()
    
    return {
        "success": True,
        "message": "Conversation archived successfully"
    }
