from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from typing import Optional
import secrets
import base64
import jwt
import os

from app.database import get_db_context, engine

router = APIRouter()

# ==================== INLINE AUTH HELPER ====================

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

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

# ==================== CLIENT PORTAL ENDPOINTS ====================

@router.post("/client-view/generate")
async def generate_client_view_link(request: Request, data: dict):
    """Practitioner generates shareable link for client"""
    practitioner_id = get_current_user_id(request)
    family_member_id = data.get('family_member_id')
    
    with get_db_context() as db:
        # Verify member exists and belongs to practitioner
        result = db.execute(text("""
            SELECT id FROM family_members 
            WHERE id = :member_id AND user_id = :user_id
        """), {'member_id': family_member_id, 'user_id': str(practitioner_id)}).fetchone()
        
        if not result:
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
        
        link = f"https://treeoflife-vn25.onrender.com/api/client/view/{token}"
        
        return {"link": link, "token": token}


@router.get("/client-view/{token}")
async def get_client_view_data(token: str):
    """Load client's protocol data via token (no auth required)"""
    
    with engine.connect() as conn:
        # Verify token
        result = conn.execute(text("""
            SELECT family_member_id, practitioner_id, is_active
            FROM client_view_tokens
            WHERE token = :token
        """), {'token': token}).fetchone()
        
        if not result or not result[2]:
            raise HTTPException(status_code=404, detail="Invalid or expired link")
        
        family_member_id = result[0]
        practitioner_id = result[1]
        
        # Update last accessed time
        conn.execute(text("""
            UPDATE client_view_tokens
            SET last_accessed = CURRENT_TIMESTAMP
            WHERE token = :token
        """), {'token': token})
        conn.commit()
        
        # Get member info
        member = conn.execute(text("""
            SELECT name FROM family_members WHERE id = :id
        """), {'id': family_member_id}).fetchone()
        
        # Get practitioner info
        practitioner = conn.execute(text("""
            SELECT full_name, email FROM users WHERE id = :id
        """), {'id': str(practitioner_id)}).fetchone()
        
        # Get active protocol assignment
        assignment = conn.execute(text("""
            SELECT id, protocol_id, current_week, completion_percentage
            FROM client_protocols
            WHERE client_id = :client_id AND status = 'active'
            LIMIT 1
        """), {'client_id': family_member_id}).fetchone()
        
        if not assignment:
            return {
                "client_name": member[0],
                "practitioner_name": practitioner[0] or practitioner[1],
                "protocol": None
            }
        
        # Get full protocol data
        protocol = conn.execute(text("""
            SELECT 
                name, description, traditions, duration_weeks,
                supplements, exercises, lifestyle_changes, nutrition,
                sleep, stress_management, weekly_notes
            FROM protocols
            WHERE id = :id
        """), {'id': assignment[1]}).fetchone()
        
        # Get recent compliance logs
        compliance = conn.execute(text("""
            SELECT week_number, compliance_score
            FROM compliance_logs
            WHERE client_protocol_id = :id
            ORDER BY week_number DESC
            LIMIT 4
        """), {'id': assignment[0]}).fetchall()
        
        # Build herbs & supplements list
        herbs_supplements = []
        
        # Add supplements
        if protocol[4]:  # supplements
            if isinstance(protocol[4], dict):
                for name, instructions in protocol[4].items():
                    if instructions:
                        herbs_supplements.append(f"{name} - {instructions}")
                    else:
                        herbs_supplements.append(name)
            elif isinstance(protocol[4], list):
                herbs_supplements.extend(protocol[4])
        
        # Add exercises
        if protocol[5]:  # exercises
            if isinstance(protocol[5], dict):
                for name, instructions in protocol[5].items():
                    if instructions:
                        herbs_supplements.append(f"{name} - {instructions}")
                    else:
                        herbs_supplements.append(name)
            elif isinstance(protocol[5], list):
                herbs_supplements.extend(protocol[5])
        
        # Build lifestyle changes list
        lifestyle_changes = []
        
        # Add lifestyle_changes field
        if protocol[6]:  # lifestyle_changes
            if isinstance(protocol[6], dict):
                for key, value in protocol[6].items():
                    if isinstance(value, dict):
                        lifestyle_changes.append(f"{key}: {', '.join(f'{k}: {v}' for k, v in value.items())}")
                    elif isinstance(value, list):
                        lifestyle_changes.append(f"{key}: {', '.join(str(v) for v in value)}")
                    else:
                        lifestyle_changes.append(f"{key}: {value}")
            elif isinstance(protocol[6], list):
                lifestyle_changes.extend(protocol[6])
        
        # Add nutrition
        if protocol[7]:  # nutrition
            if isinstance(protocol[7], dict):
                if protocol[7].get('dietary_approach'):
                    lifestyle_changes.append(f"Dietary Approach: {protocol[7]['dietary_approach']}")
                if protocol[7].get('foods_to_include'):
                    foods = protocol[7]['foods_to_include']
                    if isinstance(foods, list):
                        lifestyle_changes.append(f"Foods to Include: {', '.join(foods)}")
                    else:
                        lifestyle_changes.append(f"Foods to Include: {foods}")
                if protocol[7].get('foods_to_avoid'):
                    foods = protocol[7]['foods_to_avoid']
                    if isinstance(foods, list):
                        lifestyle_changes.append(f"Foods to Avoid: {', '.join(foods)}")
                    else:
                        lifestyle_changes.append(f"Foods to Avoid: {foods}")
        
        # Add sleep
        if protocol[8]:  # sleep
            if isinstance(protocol[8], dict):
                for key, value in protocol[8].items():
                    lifestyle_changes.append(f"Sleep - {key}: {value}")
            elif isinstance(protocol[8], str):
                lifestyle_changes.append(f"Sleep: {protocol[8]}")
        
        # Add stress management
        if protocol[9]:  # stress_management
            lifestyle_changes.append(f"Stress Management: {protocol[9]}")
        
        # Add weekly notes for current week
        if protocol[10] and isinstance(protocol[10], dict):  # weekly_notes
            week_key = f"week_{assignment[2]}"  # current_week
            if week_key in protocol[10]:
                lifestyle_changes.insert(0, f"⭐ This Week's Focus: {protocol[10][week_key]}")
        
        return {
            "client_name": member[0],
            "practitioner_name": practitioner[0] or practitioner[1],
            "protocol": {
                "name": protocol[0],
                "current_week": assignment[2],
                "total_weeks": protocol[3],
                "completion_percentage": assignment[3],
                
                # Format as current_phase for frontend compatibility
                "current_phase": {
                    "title": f"Week {assignment[2]} - {protocol[0]}",
                    "instructions": protocol[1] or "",  # description
                    "herbs_supplements": herbs_supplements,
                    "lifestyle_changes": lifestyle_changes
                },
                
                "recent_compliance": [{
                    "week": log[0],
                    "score": log[1]
                } for log in compliance]
            }
        }


@router.post("/client-view/{token}/compliance")
async def mark_client_compliance(token: str, data: dict):
    """Client marks items as complete"""
    
    compliance_score = data.get('compliance_score', 100)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT family_member_id FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        
        assignment = conn.execute(text("""
            SELECT id, current_week FROM client_protocols
            WHERE client_id = :client_id AND status = 'active'
            LIMIT 1
        """), {'client_id': family_member_id}).fetchone()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="No active protocol")
        
        conn.execute(text("""
            INSERT INTO compliance_logs (client_protocol_id, week_number, compliance_score, notes, logged_at)
            VALUES (:protocol_id, :week, :score, 'Self-reported via client view', CURRENT_TIMESTAMP)
        """), {
            'protocol_id': assignment[0],
            'week': assignment[1],
            'score': compliance_score
        })
        conn.commit()
        
        return {"success": True}


@router.post("/client-view/{token}/message")
async def send_client_message(
    token: str,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """Client sends message to practitioner with optional image"""
    
    with engine.connect() as conn:
        result = conn.execute(text("""
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
        
        conn.execute(text("""
            INSERT INTO client_messages 
            (family_member_id, practitioner_id, message_text, image_base64)
            VALUES (:member_id, :prac_id, :message, :image)
        """), {
            'member_id': family_member_id,
            'prac_id': str(practitioner_id),
            'message': message,
            'image': image_data
        })
        conn.commit()
        
        return {"success": True, "message": "Message sent to your practitioner"}


@router.get("/client-view/{token}/replies")
async def get_client_replies(token: str):
    """Client checks for practitioner replies"""
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT family_member_id
            FROM client_view_tokens
            WHERE token = :token AND is_active = true
        """), {'token': token}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invalid link")
        
        family_member_id = result[0]
        
        results = conn.execute(text("""
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
