from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from typing import Optional
import secrets
import base64

from app.database import get_db_context, engine
from app.models.user import User
from app.models.family_member import FamilyMember
from app.models.client_view_token import ClientViewToken
from app.api.dependencies import get_current_user_id

# Import protocol models (these will be created later if they don't exist)
try:
    from app.models.protocol import Protocol, ClientProtocol, ComplianceLog
except ImportError:
    # Fallback if protocol models aren't split out yet
    from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, Text, JSON, ForeignKey
    from sqlalchemy.dialects.postgresql import UUID
    from app.database import Base
    
    class Protocol(Base):
        __tablename__ = "protocols"
        id = Column(Integer, primary_key=True)
        user_id = Column(UUID(as_uuid=True), nullable=False)
        name = Column(String, nullable=False)
        traditions = Column(String)
        description = Column(Text)
        duration_weeks = Column(Integer, default=4)
        is_active = Column(Boolean, default=True)
        supplements = Column(JSON)
        exercises = Column(JSON)
        lifestyle_changes = Column(JSON)
        nutrition = Column(JSON)
        sleep = Column(JSON)
        stress_management = Column(Text)
        weekly_notes = Column(JSON)
    
    class ClientProtocol(Base):
        __tablename__ = "client_protocols"
        id = Column(Integer, primary_key=True)
        user_id = Column(UUID(as_uuid=True), nullable=False)
        client_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
        protocol_id = Column(Integer, ForeignKey('protocols.id'), nullable=False)
        start_date = Column(Date, nullable=False)
        current_week = Column(Integer, default=1)
        status = Column(String, default='active')
        completion_percentage = Column(Integer, default=0)
        assigned_at = Column(DateTime)
    
    class ComplianceLog(Base):
        __tablename__ = "compliance_logs"
        id = Column(Integer, primary_key=True)
        client_protocol_id = Column(Integer, ForeignKey('client_protocols.id'), nullable=False)
        week_number = Column(Integer, nullable=False)
        compliance_score = Column(Integer)
        notes = Column(Text)
        logged_at = Column(DateTime)

router = APIRouter()

# ==================== CLIENT PORTAL ENDPOINTS ====================

@router.post("/client-view/generate")
async def generate_client_view_link(data: dict, user_id: str = None):
    """Practitioner generates shareable link for client"""
    from fastapi import Request
    
    # Get user_id from dependency injection if available
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    practitioner_id = user_id
    family_member_id = data.get('family_member_id')
    
    with get_db_context() as db:
        member = db.query(FamilyMember).filter(
            FamilyMember.id == family_member_id,
            FamilyMember.user_id == practitioner_id
        ).first()
        
        if not member:
            raise HTTPException(status_code=404, detail="Client not found")
        
        token = secrets.token_urlsafe(32)
        
        # Deactivate old tokens
        db.execute(text("""
            UPDATE client_view_tokens 
            SET is_active = false 
            WHERE family_member_id = :member_id
        """), {'member_id': family_member_id})
        
        # Create new token
        db.execute(text("""
            INSERT INTO client_view_tokens (family_member_id, practitioner_id, token, is_active)
            VALUES (:member_id, :prac_id, :token, true)
        """), {
            'member_id': family_member_id,
            'prac_id': str(practitioner_id),
            'token': token
        })
        db.commit()
        
        link = f"https://treeoflife-vn25.onrender.com/client/view/{token}"
        
        return {"link": link, "token": token}


@router.get("/client-view/{token}")
async def get_client_view_data(token: str):
    """Load client's protocol data via token (no auth required)"""
    
    with get_db_context() as db:
        result = db.execute(text("""
            SELECT family_member_id, practitioner_id, is_active
            FROM client_view_tokens
            WHERE token = :token
        """), {'token': token}).fetchone()
        
        if not result or not result[2]:
            raise HTTPException(status_code=404, detail="Invalid or expired link")
        
        family_member_id = result[0]
        practitioner_id = result[1]
        
        # Update last accessed time
        db.execute(text("""
            UPDATE client_view_tokens
            SET last_accessed = CURRENT_TIMESTAMP
            WHERE token = :token
        """), {'token': token})
        db.commit()
        
        member = db.query(FamilyMember).filter(FamilyMember.id == family_member_id).first()
        practitioner = db.query(User).filter(User.id == practitioner_id).first()
        
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.client_id == family_member_id,
            ClientProtocol.status == 'active'
        ).first()
        
        if not assignment:
            return {
                "client_name": member.name,
                "practitioner_name": practitioner.full_name or practitioner.email,
                "protocol": None
            }
        
        protocol = db.query(Protocol).filter(Protocol.id == assignment.protocol_id).first()
        
        # ✅ SIMPLE: Just return the FULL protocol data as-is
        recent_compliance = db.query(ComplianceLog).filter(
            ComplianceLog.client_protocol_id == assignment.id
        ).order_by(ComplianceLog.week_number.desc()).limit(4).all()
        
        return {
            "client_name": member.name,
            "practitioner_name": practitioner.full_name or practitioner.email,
            "protocol": {
                "name": protocol.name,
                "description": protocol.description,
                "traditions": protocol.traditions,
                "current_week": assignment.current_week,
                "total_weeks": protocol.duration_weeks,
                "completion_percentage": assignment.completion_percentage,
                
                # ✅ PASS EVERYTHING FROM PROTOCOL AS-IS
                "supplements": protocol.supplements,
                "exercises": protocol.exercises,
                "lifestyle_changes": protocol.lifestyle_changes,
                "nutrition": protocol.nutrition,
                "sleep": protocol.sleep,
                "stress_management": protocol.stress_management,
                "weekly_notes": protocol.weekly_notes,
                
                "recent_compliance": [{
                    "week": log.week_number,
                    "score": log.compliance_score
                } for log in recent_compliance]
            }
        }


@router.post("/client-view/{token}/compliance")
async def mark_client_compliance(token: str, data: dict):
    """Client marks items as complete"""
    
    compliance_score = data.get('compliance_score', 100)
    
    with get_db_context() as db:
        result = db.execute(text("""
            SELECT family_member_id FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.client_id == family_member_id,
            ClientProtocol.status == 'active'
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="No active protocol")
        
        from datetime import datetime
        log = ComplianceLog(
            client_protocol_id=assignment.id,
            week_number=assignment.current_week,
            compliance_score=compliance_score,
            notes="Self-reported via client view"
        )
        log.logged_at = datetime.utcnow()
        db.add(log)
        db.commit()
        
        return {"success": True}


@router.post("/client-view/{token}/message")
async def send_client_message(
    token: str,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """Client sends message to practitioner with optional image"""
    
    with get_db_context() as db:
        result = db.execute(text("""
            SELECT family_member_id, practitioner_id
            FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        practitioner_id = result[1]
        
        image_data = None
        if image:
            image_content = await image.read()
            
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files allowed")
            
            if len(image_content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
            
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            image_data = f"data:{image.content_type};base64,{image_base64}"
        
        db.execute(text("""
            INSERT INTO client_messages 
            (family_member_id, practitioner_id, message_text, image_base64)
            VALUES (:member_id, :prac_id, :message, :image)
        """), {
            'member_id': family_member_id,
            'prac_id': str(practitioner_id),
            'message': message,
            'image': image_data
        })
        db.commit()
        
        return {"success": True, "message": "Message sent to your practitioner"}


@router.get("/client-view/{token}/replies")
async def get_client_replies(token: str):
    """Client checks for practitioner replies"""
    
    with get_db_context() as db:
        result = db.execute(text("""
            SELECT family_member_id
            FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        
        results = db.execute(text("""
            SELECT 
                message_text, reply_text, replied_at, created_at
            FROM client_messages
            WHERE family_member_id = :member_id
              AND reply_text IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """), {'member_id': family_member_id}).fetchall()
        
        replies = [{
            'your_question': row[0],
            'practitioner_reply': row[1],
            'replied_at': row[2].isoformat() if row[2] else None,
            'asked_at': row[3].isoformat()
        } for row in results]
        
        return {"replies": replies}


@router.get("/client/view/{token}", response_class=HTMLResponse)
async def serve_client_view_page(token: str):
    """Serve the client view HTML page"""
    html_path = "app/templates/client_view.html"
    
    try:
        with open(html_path, 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Client view page not found")
