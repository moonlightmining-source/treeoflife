"""
Tree of Life AI - Backend API with PostgreSQL Database
Multi-tradition integrative health intelligence platform

✅ LAB RESULTS FEATURE INTEGRATED
"""

from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import anthropic
import stripe
import bcrypt
import jwt
import os
import uuid
import asyncio
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Date, Float, Boolean, DateTime, ForeignKey, JSON, text
import shutil  # ✅ NEW: For file operations
import base64  # ✅ NEW: For image encoding
import json    # ✅ NEW: For JSON parsing

# Import database
from .database import (
    init_database, test_connection, get_db_context,
    User, Conversation, Message, HealthProfile,
    create_user, get_user_by_email, get_user_by_id,
    create_conversation, get_conversation, get_user_conversations,
    add_message, delete_conversation,
    get_or_create_health_profile, update_health_profile,
    engine, Base
)

# ==================== ✅ LAB RESULTS MODEL ====================

class LabResult(Base):
    """Lab result model for storing medical test results"""
    __tablename__ = "lab_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    test_type = Column(String, nullable=False)
    test_date = Column(Date, nullable=False)
    provider = Column(String, nullable=False)
    original_file_path = Column(String)
    results = Column(JSON)
    extraction_confidence = Column(Float, default=0.0)
    manually_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Initialize FastAPI app
app = FastAPI(
    title="Tree of Life AI",
    description="Multi-tradition integrative health intelligence platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["*"],
    max_age=3600,
)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    print("⚠️  WARNING: ANTHROPIC_API_KEY not set!")
    anthropic_client = None

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICES = {
    'premium': os.getenv('STRIPE_PREMIUM_PRICE_ID', 'price_YOUR_PREMIUM_ID'),
    'pro': os.getenv('STRIPE_PRO_PRICE_ID', 'price_YOUR_PRO_ID')
}

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    print("✅ Stripe initialized")
else:
    print("⚠️  WARNING: STRIPE_SECRET_KEY not set!")

SYSTEM_PROMPT = """You are Tree of Life AI, an integrative health intelligence assistant that combines wisdom from 8 major medical traditions:

1. **Western Medicine** - Evidence-based, scientific approach
2. **Ayurveda** - Constitutional types (Vata, Pitta, Kapha), doshas
3. **Traditional Chinese Medicine (TCM)** - Qi, meridians, five elements
4. **Herbal Medicine** - Plant-based remedies, phytotherapy
5. **Homeopathy** - Like cures like, energetic remedies
6. **Chiropractic** - Spinal alignment, nervous system
7. **Clinical Nutrition** - Food as medicine, micronutrients
8. **Vibrational Healing** - Sound, light, energy therapies

**Your Approach:**
- Present perspectives from MULTIPLE traditions when relevant
- Respect both scientific evidence AND traditional wisdom
- Personalize based on user's constitution and preferences
- Be educational, not diagnostic
- Always suggest "consult a practitioner" for serious concerns

Remember: You're a guide to integrative health knowledge, not a doctor."""

EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "can't breathe", "difficulty breathing",
    "severe bleeding", "heavy bleeding", "suicide", "kill myself",
    "overdose", "poisoning", "unconscious", "can't wake",
    "severe allergic", "anaphylaxis", "stroke", "paralysis"
]

# ==================== PYDANTIC MODELS ====================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ConversationRequest(BaseModel):
    initial_message: str
    image: Optional[dict] = None

class MessageRequest(BaseModel):
    message: str
    member_id: Optional[str] = None
    member_name: Optional[str] = None
    image: Optional[dict] = None

class HealthProfileUpdate(BaseModel):
    ayurvedic_dosha: Optional[str] = None
    tcm_pattern: Optional[str] = None
    body_type: Optional[str] = None
    current_conditions: Optional[List[str]] = None
    medications: Optional[List[dict]] = None
    allergies: Optional[List[str]] = None
    past_diagnoses: Optional[List[str]] = None
    diet_type: Optional[str] = None
    exercise_frequency: Optional[str] = None
    sleep_hours: Optional[int] = None
    stress_level: Optional[int] = None
    preferred_traditions: Optional[List[str]] = None
    treatment_philosophy: Optional[str] = None
    health_goals: Optional[List[str]] = None

class SubscriptionRequest(BaseModel):
    tier: str

class CancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = None

# ✅ NEW: Lab Results Models
class LabResultValue(BaseModel):
    name: str
    value: str
    unit: str
    reference_range: str

class LabResultCreate(BaseModel):
    test_type: str
    test_date: str
    provider: str
    results: List[LabResultValue]
    file_url: str

# ==================== HELPER FUNCTIONS ====================

def generate_conversation_title(text: str, max_length: int = 50) -> str:
    if len(text) <= max_length:
        return text
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."

def generate_conversation_preview(text: str, max_length: int = 100) -> str:
    if len(text) <= max_length:
        return text
    for end_char in ['. ', '! ', '? ']:
        if end_char in text[:max_length]:
            pos = text[:max_length].rfind(end_char)
            if pos > 20:
                return text[:pos + 1]
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(request: Request) -> int:
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise HTTPException(status_code=401, detail="No authorization header")
        
        if not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        return user_id
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

def detect_emergency(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in EMERGENCY_KEYWORDS)

# ==================== ✅ LAB RESULTS AI EXTRACTION ====================

async def extract_lab_data(file_path: str, provider: str, test_date: str) -> dict:
    """Extract lab test results from image/PDF using Claude Vision API"""
    
    if not anthropic_client:
        return {
            "test_type": "Blood Panel",
            "test_date": test_date,
            "provider": provider,
            "results": [],
            "confidence": 0.0,
            "error": "AI service unavailable"
        }
    
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        file_ext = os.path.splitext(file_path)[1].lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf'
        }
        media_type = media_type_map.get(file_ext, 'image/jpeg')
        
        extraction_prompt = f"""Extract ALL lab test results from this medical document.

Provider: {provider}
Date: {test_date}

Return ONLY valid JSON (no markdown):

{{
    "test_type": "Blood Panel",
    "test_date": "{test_date}",
    "provider": "{provider}",
    "results": [
        {{"name": "Glucose", "value": "95", "unit": "mg/dL", "reference_range": "70-100"}}
    ],
    "confidence": 0.95
}}

Rules: Extract ALL visible results. Use exact names. Include units and ranges. Return ONLY JSON."""

        if file_ext == '.pdf':
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": base64_data}},
                        {"type": "text", "text": extraction_prompt}
                    ]
                }]
            )
        else:
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": base64_data}},
                        {"type": "text", "text": extraction_prompt}
                    ]
                }]
            )
        
        response_text = message.content[0].text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError:
            extracted_data = {
                "test_type": "Blood Panel",
                "test_date": test_date,
                "provider": provider,
                "results": [],
                "confidence": 0.0
            }
        
        return extracted_data
        
    except Exception as e:
        print(f"Extraction error: {e}")
        return {
            "test_type": "Blood Panel",
            "test_date": test_date,
            "provider": provider,
            "results": [],
            "confidence": 0.0,
            "error": str(e)
        }

# ==================== CLAUDE AI FUNCTIONS ====================

async def get_claude_response(message: str, conversation_history: List[dict], user_profile: dict = None, image_data: dict = None) -> str:
    if not anthropic_client:
        return "⚠️ AI service is currently unavailable."
    
    if detect_emergency(message):
        return """🚨 **EMERGENCY ALERT** 🚨

This sounds like a medical emergency. 

**CALL 911 IMMEDIATELY** or go to the nearest emergency room."""
    
    try:
        system_prompt = SYSTEM_PROMPT
        if user_profile:
            profile_context = "\n\n**USER PROFILE:**"
            if user_profile.get('ayurvedic_dosha'):
                profile_context += f"\n- Ayurvedic Dosha: {user_profile['ayurvedic_dosha']}"
            if user_profile.get('preferred_traditions'):
                profile_context += f"\n- Preferred Traditions: {', '.join(user_profile['preferred_traditions'])}"
            if user_profile.get('current_conditions'):
                profile_context += f"\n- Current Concerns: {', '.join(user_profile['current_conditions'])}"
            system_prompt += profile_context
        
        messages = []
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        if image_data:
            message_content = [
                {"type": "image", "source": {"type": "base64", "media_type": image_data.get('type', 'image/jpeg'), "data": image_data['data']}},
                {"type": "text", "text": message}
            ]
        else:
            message_content = message
        
        messages.append({"role": "user", "content": message_content})
        
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=messages,
            temperature=0.7
        )
        
        return response.content[0].text
        
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        return f"I apologize, but I encountered an error: {str(e)}"

async def stream_claude_response(message: str, conversation_history: List[dict], user_profile: dict = None):
    if not anthropic_client:
        yield "⚠️ AI service is currently unavailable."
        return
    
    if detect_emergency(message):
        yield """🚨 **EMERGENCY ALERT** 🚨

**CALL 911 IMMEDIATELY** or go to the nearest emergency room."""
        return
    
    try:
        system_prompt = SYSTEM_PROMPT
        if user_profile:
            profile_context = "\n\n**USER PROFILE:**"
            if user_profile.get('ayurvedic_dosha'):
                profile_context += f"\n- Ayurvedic Dosha: {user_profile['ayurvedic_dosha']}"
            system_prompt += profile_context
        
        messages = []
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})
        
        with anthropic_client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=messages,
            temperature=0.7
        ) as stream:
            for text in stream.text_stream:
                yield text
                await asyncio.sleep(0.01)
                
    except Exception as e:
        yield f"\n\n⚠️ Error: {str(e)}"

# ==================== MIDDLEWARE ====================

@app.middleware("http")
async def handle_options(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600",
            }
        )
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    print(f"❌ Unhandled exception: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={"Access-Control-Allow-Origin": "*"}
    )

# ==================== STARTUP ====================

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Tree of Life AI...")
    if test_connection():
        print("✅ Database connected!")
        init_database()
        
        try:
            with engine.connect() as conn:
                # Check image_data column
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'messages' AND column_name = 'image_data'
                """))
                
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE messages ADD COLUMN image_data JSON"))
                    conn.commit()
                    print("✅ image_data column added")
                
                # ✅ NEW: Check lab_results table
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'lab_results'
                """))
                
                if not result.fetchone():
                    print("➕ Creating lab_results table...")
                    conn.execute(text("""
                        CREATE TABLE lab_results (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR NOT NULL,
                            test_type VARCHAR(100) NOT NULL,
                            test_date DATE NOT NULL,
                            provider VARCHAR(200) NOT NULL,
                            original_file_path VARCHAR(500),
                            results JSONB,
                            extraction_confidence FLOAT DEFAULT 0.0,
                            manually_verified BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        )
                    """))
                    conn.execute(text("CREATE INDEX idx_lab_results_user_id ON lab_results(user_id)"))
                    conn.execute(text("CREATE INDEX idx_lab_results_test_date ON lab_results(test_date DESC)"))
                    conn.commit()
                    print("✅ lab_results table created!")
                else:
                    print("✅ lab_results table exists")
                    
        except Exception as e:
            print(f"⚠️  Migration warning: {e}")
        
        print("✅ Server ready!")

@app.get("/")
async def root():
    return {
        "message": "Tree of Life AI - Integrative Health Intelligence Platform",
        "version": "2.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if test_connection() else "disconnected",
        "ai_service": "available" if anthropic_client else "unavailable"
    }

# ==================== AUTH ====================

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    try:
        with get_db_context() as db:
            existing_user = get_user_by_email(db, request.email)
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
            
            password_hash = hash_password(request.password)
            user = create_user(db, request.email, request.name, password_hash)
            token = create_token(str(user.id), user.email)
            
            return {
                "message": "Registration successful",
                "token": token,
                "user": {"id": str(user.id), "email": user.email, "name": user.name}
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    try:
        with get_db_context() as db:
            user = get_user_by_email(db, request.email)
            if not user or not verify_password(request.password, user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            token = create_token(str(user.id), user.email)
            return {
                "message": "Login successful",
                "token": token,
                "user": {"id": str(user.id), "email": user.email, "name": user.name}
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CHAT ====================

@app.post("/api/chat/conversations")
async def create_new_conversation(request: ConversationRequest, http_request: Request):
    user_id = get_current_user_id(http_request)
    
    with get_db_context() as db:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile = get_or_create_health_profile(db, user_id)
        user_profile = {
            'ayurvedic_dosha': profile.ayurvedic_dosha,
            'preferred_traditions': profile.preferred_traditions or []
        }
        
        conversation_id = str(uuid.uuid4())
        title = generate_conversation_title(request.initial_message)
        preview = generate_conversation_preview(request.initial_message)
        
        conversation = create_conversation(db, conversation_id, user_id, title, preview)
        add_message(db, conversation_id, "user", request.initial_message, image_data=request.image)
        
        response_text = await get_claude_response(request.initial_message, [], user_profile, image_data=request.image)
        add_message(db, conversation_id, "assistant", response_text)
        
        return {
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "preview": conversation.preview,
                "created_at": conversation.created_at.isoformat()
            },
            "messages": [
                {"role": "user", "content": request.initial_message},
                {"role": "assistant", "content": response_text}
            ]
        }

@app.get("/api/chat/conversations")
async def get_conversations(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversations = get_user_conversations(db, user_id)
        return {
            "conversations": [
                {
                    "id": str(conv.id),
                    "title": conv.title,
                    "preview": conv.preview,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                }
                for conv in conversations
            ]
        }

@app.get("/api/chat/conversations/{conversation_id}")
async def get_single_conversation(conversation_id: str, request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversation = get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if str(conversation.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        return {
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "preview": conversation.preview,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            },
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "image": msg.image_data if hasattr(msg, 'image_data') and msg.image_data else None
                }
                for msg in conversation.messages
            ]
        }

@app.post("/api/chat/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: MessageRequest, http_request: Request):
    user_id = get_current_user_id(http_request)
    
    with get_db_context() as db:
        conversation = get_conversation(db, conversation_id)
        if not conversation or str(conversation.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        profile = get_or_create_health_profile(db, user_id)
        user_profile = {
            'ayurvedic_dosha': profile.ayurvedic_dosha,
            'preferred_traditions': profile.preferred_traditions or []
        }
        
        history = [{"role": msg.role, "content": msg.content} for msg in conversation.messages]
        add_message(db, conversation_id, "user", request.message, image_data=request.image)
        
        response_text = await get_claude_response(request.message, history, user_profile, image_data=request.image)
        assistant_msg = add_message(db, conversation_id, "assistant", response_text)
        
        return {
            "message": {
                "role": "assistant",
                "content": response_text,
                "timestamp": assistant_msg.timestamp.isoformat()
            }
        }

@app.delete("/api/chat/conversations/{conversation_id}")
async def delete_conv(conversation_id: str, request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversation = get_conversation(db, conversation_id)
        if not conversation or str(conversation.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        delete_conversation(db, conversation_id)
        return {"message": "Conversation deleted"}

# ==================== HEALTH PROFILE ====================

@app.get("/api/health/profile")
async def get_health_profile(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        profile = get_or_create_health_profile(db, user_id)
        return {
            "profile": {
                "ayurvedic_dosha": profile.ayurvedic_dosha,
                "tcm_pattern": profile.tcm_pattern,
                "current_conditions": profile.current_conditions or [],
                "medications": profile.medications or [],
                "preferred_traditions": profile.preferred_traditions or []
            }
        }

@app.put("/api/health/profile")
async def update_profile(profile_update: HealthProfileUpdate, request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        update_data = profile_update.dict(exclude_unset=True)
        profile = update_health_profile(db, user_id, **update_data)
        return {"message": "Profile updated successfully"}

# ==================== ✅ LAB RESULTS ENDPOINTS ====================

UPLOAD_DIR = "uploads/lab_results"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/lab-results/upload")
async def upload_lab_result(
    file: UploadFile = File(...),
    provider: str = Form(...),
    test_date: str = Form(...),
    http_request: Request = None
):
    """Upload lab result file and extract data using AI"""
    user_id = get_current_user_id(http_request)
    
    try:
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        user_dir = os.path.join(UPLOAD_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = os.path.splitext(file.filename)[1]
        filename = f"{timestamp}{file_ext}"
        file_path = os.path.join(user_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"📤 File uploaded: {file_path}")
        
        extracted_data = await extract_lab_data(file_path, provider, test_date)
        extracted_data['file_url'] = file_path
        
        print(f"🤖 Extraction complete: {len(extracted_data.get('results', []))} results")
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/lab-results/save")
async def save_lab_result(data: LabResultCreate, http_request: Request):
    """Save confirmed lab results to database"""
    user_id = get_current_user_id(http_request)
    
    try:
        results_json = [result.dict() for result in data.results]
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO lab_results 
                (user_id, test_type, test_date, provider, original_file_path, results, manually_verified)
                VALUES (:user_id, :test_type, :test_date, :provider, :file_path, :results, TRUE)
                RETURNING id
            """), {
                'user_id': str(user_id),
                'test_type': data.test_type,
                'test_date': data.test_date,
                'provider': data.provider,
                'file_path': data.file_url,
                'results': json.dumps(results_json)
            })
            conn.commit()
            new_id = result.fetchone()[0]
        
        print(f"✅ Lab results saved (ID: {new_id})")
        
        return {"status": "success", "id": new_id, "message": "Lab results saved successfully"}
        
    except Exception as e:
        print(f"❌ Save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lab-results")
async def get_lab_results(http_request: Request):
    """Get all lab results for current user"""
    user_id = get_current_user_id(http_request)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, test_type, test_date, provider, results, created_at
                FROM lab_results
                WHERE user_id = :user_id
                ORDER BY test_date DESC
            """), {'user_id': str(user_id)})
            
            results = []
            for row in result:
                results.append({
                    'id': row[0],
                    'test_type': row[1],
                    'test_date': row[2].isoformat(),
                    'provider': row[3],
                    'results': row[4] if isinstance(row[4], list) else json.loads(row[4]) if row[4] else [],
                    'created_at': row[5].isoformat()
                })
        
        print(f"📊 Retrieved {len(results)} lab results")
        
        return results
        
    except Exception as e:
        print(f"❌ Get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/lab-results/{result_id}")
async def delete_lab_result(result_id: int, http_request: Request):
    """Delete a lab result"""
    user_id = get_current_user_id(http_request)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT user_id, original_file_path FROM lab_results WHERE id = :id
            """), {'id': result_id})
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Lab result not found")
            
            if str(row[0]) != str(user_id):
                raise HTTPException(status_code=403, detail="Not authorized")
            
            if row[1] and os.path.exists(row[1]):
                os.remove(row[1])
            
            conn.execute(text("DELETE FROM lab_results WHERE id = :id"), {'id': result_id})
            conn.commit()
        
        print(f"🗑️ Lab result {result_id} deleted")
        
        return {"status": "success", "message": "Lab result deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SUBSCRIPTIONS ====================

@app.post("/api/subscription/create-checkout")
async def create_checkout_session(request: SubscriptionRequest, http_request: Request):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    user_id = get_current_user_id(http_request)
    
    with get_db_context() as db:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        price_id = STRIPE_PRICES.get(request.tier)
        if not price_id or 'YOUR' in price_id:
            raise HTTPException(status_code=400, detail="Invalid tier")
        
        try:
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(email=user.email, metadata={'user_id': str(user.id)})
                user.stripe_customer_id = customer.id
                db.commit()
            
            checkout_session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url=os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/subscriptions.html?success=true',
                cancel_url=os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/subscriptions.html?cancelled=true',
                metadata={'user_id': str(user.id), 'tier': request.tier}
            )
            
            return {"checkout_url": checkout_session.url}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/subscription/status")
async def get_subscription_status(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "tier": user.subscription_tier,
            "status": user.subscription_status,
            "has_active_subscription": user.subscription_tier in ['premium', 'pro'] and user.subscription_status == 'active'
        }

# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
