"""
Client Portal API endpoints
Handles client view tokens and portal access
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.auth import get_current_user_id  # ← FIXED: Import from auth.py instead of main.py
from app.main import get_db_context, FamilyMember, User, engine
from sqlalchemy import text
from datetime import datetime
import secrets

router = APIRouter()

# Dependency to get current user with db access
def get_current_user_dep(request: Request):
    """Dependency to get current user info"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.full_name,
            "subscription_tier": user.subscription_tier or 'free'
        }

class GenerateLinkRequest(BaseModel):
    client_id: int

class ClientPortalAccess(BaseModel):
    token: str

# ==================== CLIENT VIEW TOKEN ENDPOINTS ====================

@router.post("/client-portal/generate-link")
async def generate_client_link(
    data: GenerateLinkRequest,
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
):
    """Generate a secure view link for a client"""
    user_id = current_user["id"]
    
    with get_db_context() as db:
        # Verify client belongs to this practitioner
        member = db.query(FamilyMember).filter(
            FamilyMember.id == data.client_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not member:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Store token in database
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO client_view_tokens (family_member_id, practitioner_id, token, created_at, is_active)
                VALUES (:member_id, :practitioner_id, :token, :created_at, true)
            """), {
                'member_id': data.client_id,
                'practitioner_id': user_id,
                'token': token,
                'created_at': datetime.now()
            })
            conn.commit()
        
        # Generate full URL
        base_url = "https://treeoflifeai.com"
        link_url = f"{base_url}/client-view.html?token={token}"
        
        return {
            "success": True,
            "link": link_url,
            "token": token,
            "client_name": member.name
        }


@router.get("/client-portal/verify-token/{token}")
async def verify_client_token(token: str):
    """Verify if a client portal token is valid"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT cvt.id, cvt.family_member_id, cvt.practitioner_id, cvt.is_active,
                   fm.name as client_name,
                   u.full_name as practitioner_name
            FROM client_view_tokens cvt
            JOIN family_members fm ON fm.id = cvt.family_member_id
            JOIN users u ON u.id = cvt.practitioner_id
            WHERE cvt.token = :token
            AND cvt.is_active = true
        """), {'token': token})
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Invalid or expired token")
        
        # Update last_accessed timestamp
        conn.execute(text("""
            UPDATE client_view_tokens
            SET last_accessed = :now
            WHERE token = :token
        """), {'now': datetime.now(), 'token': token})
        conn.commit()
        
        return {
            "valid": True,
            "client_id": row[1],
            "client_name": row[3],
            "practitioner_name": row[4]
        }


@router.delete("/client-portal/revoke-token/{token}")
async def revoke_client_token(
    token: str,
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
):
    """Revoke a client portal token"""
    user_id = current_user["id"]
    
    with engine.connect() as conn:
        # Verify token belongs to this practitioner
        result = conn.execute(text("""
            SELECT id FROM client_view_tokens
            WHERE token = :token AND practitioner_id = :user_id
        """), {'token': token, 'user_id': user_id})
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Deactivate token
        conn.execute(text("""
            UPDATE client_view_tokens
            SET is_active = false
            WHERE token = :token
        """), {'token': token})
        conn.commit()
        
        return {"success": True, "message": "Token revoked"}


@router.get("/client-portal/active-links")
async def get_active_links(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
):
    """Get all active client portal links for the current practitioner"""
    user_id = current_user["id"]
    
    with engine.connect() as conn:
        results = conn.execute(text("""
            SELECT cvt.token, cvt.created_at, cvt.last_accessed,
                   fm.id as client_id, fm.name as client_name
            FROM client_view_tokens cvt
            JOIN family_members fm ON fm.id = cvt.family_member_id
            WHERE cvt.practitioner_id = :user_id
            AND cvt.is_active = true
            ORDER BY cvt.created_at DESC
        """), {'user_id': user_id})
        
        links = []
        base_url = "https://treeoflifeai.com"
        
        for row in results:
            links.append({
                'token': row[0],
                'url': f"{base_url}/client-view.html?token={row[0]}",
                'created_at': row[1].isoformat() if row[1] else None,
                'last_accessed': row[2].isoformat() if row[2] else None,
                'client_id': row[3],
                'client_name': row[4]
            })
        
        return {'links': links}
