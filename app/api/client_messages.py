"""
Client Messages API Routes - Standalone version
Handles practitioner viewing of client portal submissions
"""
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from datetime import datetime
import os
import jwt

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_current_user_id(request: Request) -> str:
    """Extract user ID from JWT token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

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
    
    with get_db() as db:
        # Verify member belongs to current user
        member = db.execute(text("""
            SELECT id FROM family_members 
            WHERE id = :member_id AND user_id = :user_id
        """), {'member_id': member_id, 'user_id': current_user_id}).fetchone()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found or does not belong to you"
            )
        
        # Get all messages from this client
        messages = db.execute(text("""
            SELECT id, family_member_id, message_text, image_base64, 
                   is_read, replied_at, reply_text, created_at
            FROM client_messages
            WHERE family_member_id = :member_id
            ORDER BY created_at DESC
        """), {'member_id': member_id}).fetchall()
        
        return {
            "success": True,
            "messages": [{
                "id": str(row[0]),
                "family_member_id": row[1],
                "message_text": row[2],
                "image_base64": row[3],
                "is_read": row[4],
                "replied_at": row[5].isoformat() if row[5] else None,
                "reply_text": row[6],
                "created_at": row[7].isoformat() if row[7] else None
            } for row in messages]
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
    
    with get_db() as db:
        # Verify member belongs to current user
        member = db.execute(text("""
            SELECT id FROM family_members 
            WHERE id = :member_id AND user_id = :user_id
        """), {'member_id': member_id, 'user_id': current_user_id}).fetchone()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Count unread messages (is_read = False)
        unread_count = db.execute(text("""
            SELECT COUNT(*) 
            FROM client_messages
            WHERE family_member_id = :member_id AND is_read = false
        """), {'member_id': member_id}).scalar()
        
        return {
            "success": True,
            "unread_count": unread_count or 0
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
    
    with get_db() as db:
        # Verify the message's client belongs to current user
        result = db.execute(text("""
            SELECT cm.id
            FROM client_messages cm
            JOIN family_members fm ON cm.family_member_id = fm.id
            WHERE cm.id = :message_id AND fm.user_id = :user_id
        """), {'message_id': message_id, 'user_id': current_user_id}).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or you don't have permission"
            )
        
        # Mark as read
        db.execute(text("""
            UPDATE client_messages
            SET is_read = true
            WHERE id = :message_id
        """), {'message_id': message_id})
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
    
    with get_db() as db:
        # Get unread counts per client
        results = db.execute(text("""
            SELECT 
                fm.id as client_id,
                fm.name as client_name,
                COUNT(cm.id) as unread_count
            FROM family_members fm
            LEFT JOIN client_messages cm ON cm.family_member_id = fm.id AND cm.is_read = false
            WHERE fm.user_id = :user_id
            GROUP BY fm.id, fm.name
            HAVING COUNT(cm.id) > 0
        """), {'user_id': current_user_id}).fetchall()
        
        summary = {
            "total_unread": 0,
            "clients": []
        }
        
        for row in results:
            summary["clients"].append({
                "client_id": row[0],
                "client_name": row[1],
                "unread_count": row[2]
            })
            summary["total_unread"] += row[2]
        
        return {
            "success": True,
            "summary": summary
        }
