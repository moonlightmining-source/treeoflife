"""
Client Messages API Routes
Handles practitioner viewing of client portal submissions
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.main import get_db_context, get_current_user_id, FamilyMember, ClientMessage

router = APIRouter()


@router.get("/client-messages/{member_id}")
async def get_client_messages(
    member_id: int,
    request: Request
):
    """
    Get all messages submitted by a specific client through their portal
    
    Returns messages with text, images, and compliance checkbox data
    Ordered by most recent first
    """
    current_user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Verify member belongs to current user
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user_id
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found or does not belong to you"
            )
        
        # Get all messages from this client
        messages = db.query(ClientMessage).filter(
            ClientMessage.family_member_id == member_id
        ).order_by(ClientMessage.created_at.desc()).all()
        
        return {
            "success": True,
            "messages": [{
                "id": str(msg.id),
                "family_member_id": msg.family_member_id,
                "message_text": msg.message_text,
                "image_base64": msg.image_base64,
                "is_read": msg.is_read,
                "replied_at": msg.replied_at.isoformat() if msg.replied_at else None,
                "reply_text": msg.reply_text,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            } for msg in messages]
        }


@router.get("/client-messages/{member_id}/count")
async def get_unread_count(
    member_id: int,
    request: Request
):
    """
    Get count of unread messages for a specific client
    
    Used for displaying unread badges in the UI
    """
    current_user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Verify member belongs to current user
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.user_id == current_user_id
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Count unread messages (is_read = False)
        unread_count = db.query(ClientMessage).filter(
            ClientMessage.family_member_id == member_id,
            ClientMessage.is_read == False
        ).count()
        
        return {
            "success": True,
            "unread_count": unread_count
        }


@router.post("/client-messages/{message_id}/read")
async def mark_message_as_read(
    message_id: str,
    request: Request
):
    """
    Mark a client message as read
    
    Sets the is_read flag to True
    Used when practitioner views a message
    """
    current_user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Get the message
        message = db.query(ClientMessage).filter(
            ClientMessage.id == message_id
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Verify the message's client belongs to current user
        member = db.query(FamilyMember).filter(
            FamilyMember.id == message.family_member_id,
            FamilyMember.user_id == current_user_id
        ).first()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this message"
            )
        
        # Mark as read
        message.is_read = True
        db.commit()
        
        return {
            "success": True,
            "message": "Message marked as read"
        }


@router.get("/client-messages/unread-summary")
async def get_unread_summary(
    request: Request
):
    """
    Get summary of unread messages across all clients
    
    Returns total unread count and per-client breakdown
    Useful for dashboard notifications
    """
    current_user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Get all members belonging to current user
        members = db.query(FamilyMember).filter(
            FamilyMember.user_id == current_user_id
        ).all()
        
        summary = {
            "total_unread": 0,
            "clients": []
        }
        
        for member in members:
            unread_count = db.query(ClientMessage).filter(
                ClientMessage.family_member_id == member.id,
                ClientMessage.is_read == False
            ).count()
            
            if unread_count > 0:
                summary["clients"].append({
                    "client_id": member.id,
                    "client_name": member.name,
                    "unread_count": unread_count
                })
                summary["total_unread"] += unread_count
        
        return {
            "success": True,
            "summary": summary
        }
