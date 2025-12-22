"""
Tree of Life AI - Backend API with PostgreSQL Database
Multi-tradition integrative health intelligence platform
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import anthropic
import stripe  # ✅ STRIPE ADDED
import bcrypt
import jwt
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Import database (relative import - same package)
from .database import (
    init_database, test_connection, get_db_context,
    User, Conversation, Message, HealthProfile,
    create_user, get_user_by_email, get_user_by_id,
    create_conversation, get_conversation, get_user_conversations,
    add_message, delete_conversation,
    get_or_create_health_profile, update_health_profile
)

# Initialize FastAPI app
app = FastAPI(
    title="Tree of Life AI",
    description="Multi-tradition integrative health intelligence platform",
    version="2.0.0"
)

# CORS Configuration - Explicitly allow Authorization header
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins temporarily
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],  # Explicit headers
    expose_headers=["*"],
    max_age=3600,
)

# Environment Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize Anthropic client
if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    print("⚠️  WARNING: ANTHROPIC_API_KEY not set!")
    anthropic_client = None

# ==================== STRIPE CONFIGURATION ====================

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Stripe Price IDs (UPDATE THESE after creating products in Stripe!)
STRIPE_PRICES = {
    'premium': os.getenv('STRIPE_PREMIUM_PRICE_ID', 'price_YOUR_PREMIUM_ID'),
    'pro': os.getenv('STRIPE_PRO_PRICE_ID', 'price_YOUR_PRO_ID')
}

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    print("✅ Stripe initialized")
    print(f"📋 Stripe prices configured:")
    print(f"   Premium: {STRIPE_PRICES['premium']}")
    print(f"   Pro: {STRIPE_PRICES['pro']}")
    
    # Warn if still using placeholders
    if STRIPE_PRICES['premium'] == 'price_YOUR_PREMIUM_ID':
        print("⚠️  WARNING: STRIPE_PREMIUM_PRICE_ID not set - still using placeholder!")
    if STRIPE_PRICES['pro'] == 'price_YOUR_PRO_ID':
        print("⚠️  WARNING: STRIPE_PRO_PRICE_ID not set - still using placeholder!")
else:
    print("⚠️  WARNING: STRIPE_SECRET_KEY not set!")

# ==================== SYSTEM PROMPT ====================

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

**Safety First:**
- Detect emergencies (chest pain, severe symptoms, suicidal thoughts)
- Warn about herb-drug interactions
- Never recommend stopping prescribed medications
- Emphasize this is educational, not medical advice

**Tone:**
- Professional yet warm
- Clear and educational
- Empowering and non-judgmental
- Evidence-informed but open to traditional practices

Remember: You're a guide to integrative health knowledge, not a doctor."""

EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "can't breathe", "difficulty breathing",
    "severe bleeding", "heavy bleeding", "suicide", "kill myself",
    "overdose", "poisoning", "unconscious", "can't wake",
    "severe allergic", "anaphylaxis", "stroke", "paralysis",
    "severe head injury", "compound fracture", "seizure"
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
    image: Optional[dict] = None  # ✅ FIX: Support images in new conversations

class MessageRequest(BaseModel):
    message: str
    member_id: Optional[str] = None  # For family member chat
    member_name: Optional[str] = None  # For family member chat
    image: Optional[dict] = None  # ✅ NEW: Image data {type: str, data: str}

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

# ✅ STRIPE MODELS ADDED
class SubscriptionRequest(BaseModel):
    tier: str  # 'premium' or 'pro'

class CancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = None

# ==================== HELPER FUNCTIONS ====================

def generate_conversation_title(text: str, max_length: int = 50) -> str:
    """Generate a title from the first message"""
    if len(text) <= max_length:
        return text
    # Truncate at word boundary
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."

def generate_conversation_preview(text: str, max_length: int = 100) -> str:
    """Generate a preview from the first message"""
    if len(text) <= max_length:
        return text
    # Try to break at sentence
    for end_char in ['. ', '! ', '? ']:
        if end_char in text[:max_length]:
            pos = text[:max_length].rfind(end_char)
            if pos > 20:  # Ensure minimum length
                return text[:pos + 1]
    # Fall back to word boundary
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."

def hash_password(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    """Create JWT token"""
    payload = {
        'user_id': user_id,  # UUID as string
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(request: Request) -> int:
    """Get current user ID from token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            print("❌ No Authorization header")
            raise HTTPException(status_code=401, detail="No authorization header")
        
        if not auth_header.startswith('Bearer '):
            print(f"❌ Invalid auth header format: {auth_header[:20]}")
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = auth_header.split(' ')[1]
        print(f"✅ Token received: {token[:20]}...")
        
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        if not user_id:
            print("❌ No user_id in token payload")
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        print(f"✅ Authenticated user: {user_id}")
        return user_id
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"❌ Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def detect_emergency(message: str) -> bool:
    """Detect emergency keywords in message"""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in EMERGENCY_KEYWORDS)

# ==================== CLAUDE AI FUNCTIONS ====================

async def get_claude_response(message: str, conversation_history: List[dict], user_profile: dict = None, image_data: dict = None) -> str:
    """Get response from Claude API with optional image support"""
    if not anthropic_client:
        return "⚠️ AI service is currently unavailable. Please check your API configuration."
    
    # Check for emergency
    if detect_emergency(message):
        return """🚨 **EMERGENCY ALERT** 🚨

This sounds like a medical emergency. 

**CALL 911 IMMEDIATELY** or go to the nearest emergency room.

Do not wait. Do not try home remedies. Get professional medical help RIGHT NOW.

After the emergency is handled, we're here to support your ongoing health journey."""
    
    try:
        # Build context with user profile if available
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
        
        # Add conversation history
        messages = []
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # ✅ BUILD MESSAGE WITH OPTIONAL IMAGE
        if image_data:
            # Include both image and text
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_data.get('type', 'image/jpeg'),
                        "data": image_data['data']
                    }
                },
                {
                    "type": "text",
                    "text": message
                }
            ]
            print(f"📸 Processing message with image: {image_data.get('type', 'unknown')}")
        else:
            # Text only
            message_content = message
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message_content
        })
        
        # Call Claude API
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
        return f"I apologize, but I encountered an error: {str(e)}\n\nPlease try again in a moment."

async def stream_claude_response(message: str, conversation_history: List[dict], user_profile: dict = None):
    """Stream response from Claude API"""
    if not anthropic_client:
        yield "⚠️ AI service is currently unavailable."
        return
    
    # Check for emergency
    if detect_emergency(message):
        yield """🚨 **EMERGENCY ALERT** 🚨

This sounds like a medical emergency. 

**CALL 911 IMMEDIATELY** or go to the nearest emergency room.

Do not wait. Do not try home remedies. Get professional medical help RIGHT NOW."""
        return
    
    try:
        # Build system prompt with profile
        system_prompt = SYSTEM_PROMPT
        if user_profile:
            profile_context = "\n\n**USER PROFILE:**"
            if user_profile.get('ayurvedic_dosha'):
                profile_context += f"\n- Ayurvedic Dosha: {user_profile['ayurvedic_dosha']}"
            if user_profile.get('preferred_traditions'):
                profile_context += f"\n- Preferred Traditions: {', '.join(user_profile['preferred_traditions'])}"
            system_prompt += profile_context
        
        # Build messages
        messages = []
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})
        
        # Stream from Claude
        with anthropic_client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=messages,
            temperature=0.7
        ) as stream:
            for text in stream.text_stream:
                yield text
                await asyncio.sleep(0.01)  # Small delay for smooth streaming
                
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        yield f"\n\n⚠️ Error: {str(e)}"

# ==================== API ROUTES ====================

# ==================== MIDDLEWARE ====================

@app.middleware("http")
async def handle_options(request: Request, call_next):
    """Handle OPTIONS requests for CORS preflight"""
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",  # Explicit!
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600",
            }
        )
    
    # Process the request
    response = await call_next(request)
    
    # Add CORS headers to ALL responses (including errors)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept"
    
    return response

# Exception handler for all HTTPExceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper CORS headers"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
        }
    )

# Exception handler for ALL other exceptions (500 errors)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with CORS headers"""
    print(f"❌ Unhandled exception: {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "type": type(exc).__name__
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
        }
    )

# ==================== STARTUP EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting Tree of Life AI...")
    print("📊 Testing database connection...")
    if test_connection():
        print("✅ Database connected!")
        print("🔧 Initializing database schema...")
        init_database()
        print("✅ Server ready!")
    else:
        print("❌ Database connection failed!")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Tree of Life AI - Integrative Health Intelligence Platform",
        "version": "2.0.0",
        "status": "operational",
        "database": "PostgreSQL (persistent storage)",
        "api_docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = test_connection()
    return {
        "status": "healthy" if db_status else "degraded",
        "database": "connected" if db_status else "disconnected",
        "ai_service": "available" if anthropic_client else "unavailable",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== AUTHENTICATION ====================

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    try:
        print(f"📝 Registration attempt: {request.email}")
        
        with get_db_context() as db:
            # Check if user exists
            print(f"  Checking if user exists...")
            existing_user = get_user_by_email(db, request.email)
            if existing_user:
                print(f"  ❌ Email already registered: {request.email}")
                raise HTTPException(status_code=400, detail="Email already registered")
            
            print(f"  ✅ Email available")
            
            # Create user
            print(f"  Hashing password...")
            password_hash = hash_password(request.password)
            
            print(f"  Creating user in database...")
            user = create_user(db, request.email, request.name, password_hash)
            
            print(f"  ✅ User created: {user.email}")
            
            # Create token
            print(f"  Creating token...")
            token = create_token(str(user.id), user.email)  # Convert UUID to string
            
            print(f"✅ User registered successfully: {user.email}")
            
            return {
                "message": "Registration successful",
                "token": token,
                "user": {
                    "id": str(user.id),  # Convert UUID to string for JSON
                    "email": user.email,
                    "name": user.name
                }
            }
    
    except HTTPException:
        # Re-raise HTTP exceptions (400, etc)
        raise
    except Exception as e:
        # Log any other errors
        print(f"❌ Registration error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login user"""
    try:
        print(f"🔐 Login attempt: {request.email}")
        
        with get_db_context() as db:
            # Get user
            print(f"  Looking up user in database...")
            user = get_user_by_email(db, request.email)
            
            if not user:
                print(f"  ❌ User not found: {request.email}")
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            print(f"  ✅ User found: {user.email}")
            
            # Verify password
            print(f"  Verifying password...")
            if not verify_password(request.password, user.password_hash):
                print(f"  ❌ Invalid password")
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            print(f"  ✅ Password correct")
            
            # Create token
            print(f"  Creating token...")
            token = create_token(str(user.id), user.email)  # Convert UUID to string
            
            print(f"✅ User logged in successfully: {user.email}")
            
            return {
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": str(user.id),  # Convert UUID to string for JSON
                    "email": user.email,
                    "name": user.name
                }
            }
    
    except HTTPException:
        # Re-raise HTTP exceptions (401, etc)
        raise
    except Exception as e:
        # Log any other errors
        print(f"❌ Login error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

# ==================== CHAT / CONVERSATIONS ====================

@app.post("/api/chat/conversations")
async def create_new_conversation(request: ConversationRequest, http_request: Request):
    """Create a new conversation"""
    user_id = get_current_user_id(http_request)
    
    with get_db_context() as db:
        # Get user
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's health profile
        profile = get_or_create_health_profile(db, user_id)
        user_profile = {
            'ayurvedic_dosha': profile.ayurvedic_dosha,
            'preferred_traditions': profile.preferred_traditions or [],
            'current_conditions': profile.current_conditions or []
        }
        
        # Generate conversation ID
        conversation_id = str(uuid.uuid4())
        
        # Generate title and preview
        title = generate_conversation_title(request.initial_message)
        preview = generate_conversation_preview(request.initial_message)
        
        # Create conversation
        conversation = create_conversation(db, conversation_id, user_id, title, preview)
        
        # ✅ Add user message WITH IMAGE DATA
        add_message(db, conversation_id, "user", request.initial_message, image_data=request.image)
        
        print(f"💬 Creating conversation for {user.email}")
        
        # ✅ FIX: Get Claude response WITH IMAGE SUPPORT
        if request.image:
            print(f"📸 New conversation with image: {request.image.get('type', 'unknown')}")
        
        response_text = await get_claude_response(
            request.initial_message, 
            [], 
            user_profile,
            image_data=request.image  # ✅ FIX: Pass image data
        )
        
        # Add assistant message
        add_message(db, conversation_id, "assistant", response_text)
        
        print(f"✅ Claude response received ({len(response_text)} chars)")
        
        return {
            "conversation": {
                "id": str(conversation.id),  # Convert UUID to string
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
    """Get all conversations for current user"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversations = get_user_conversations(db, user_id)
        
        return {
            "conversations": [
                {
                    "id": str(conv.id),  # Convert UUID to string
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
    """Get a specific conversation with all messages"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversation = get_conversation(db, conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # 🔧 FIX: Convert both to strings for comparison
        if str(conversation.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        return {
            "conversation": {
                "id": str(conversation.id),  # Convert UUID to string
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
                    "created_at": msg.timestamp.isoformat() if msg.timestamp else None,  # ✅ FIX: Use timestamp field
                    "image": msg.image_data if hasattr(msg, 'image_data') and msg.image_data else None  # ✅ NEW: Return image data
                }
                for msg in conversation.messages
            ]
        }

@app.post("/api/chat/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: MessageRequest, http_request: Request):
    """Send a message in a conversation"""
    user_id = get_current_user_id(http_request)
    
    with get_db_context() as db:
        # Get conversation
        conversation = get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # 🔧 FIX: Convert both to strings for comparison (THIS WAS THE BUG!)
        if str(conversation.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Get user profile
        profile = get_or_create_health_profile(db, user_id)
        user_profile = {
            'ayurvedic_dosha': profile.ayurvedic_dosha,
            'preferred_traditions': profile.preferred_traditions or [],
            'current_conditions': profile.current_conditions or []
        }
        
        # Get conversation history
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages
        ]
        
        # ✅ Add user message WITH IMAGE DATA
        add_message(db, conversation_id, "user", request.message, image_data=request.image)
        
        # ✅ FIX: Add debug logging for images
        if request.image:
            print(f"📸 Message with image: {request.image.get('type', 'unknown')} ({len(request.image.get('data', '')) // 1024}KB)")
        
        # ✅ Get Claude response WITH IMAGE SUPPORT
        response_text = await get_claude_response(
            request.message, 
            history, 
            user_profile,
            image_data=request.image  # Pass image data if present
        )
        
        # Add assistant message
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
    """Delete a conversation"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversation = get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # 🔧 FIX: Convert both to strings for comparison
        if str(conversation.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        delete_conversation(db, conversation_id)
        
        return {"message": "Conversation deleted"}

@app.get("/api/chat/stream")
async def stream_chat(message: str, conversation_id: str, request: Request):
    """Stream chat response"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversation = get_conversation(db, conversation_id)
        if not conversation or str(conversation.user_id) != str(user_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        profile = get_or_create_health_profile(db, user_id)
        user_profile = {
            'ayurvedic_dosha': profile.ayurvedic_dosha,
            'preferred_traditions': profile.preferred_traditions or []
        }
        
        history = [{"role": msg.role, "content": msg.content} for msg in conversation.messages]
        
        return StreamingResponse(
            stream_claude_response(message, history, user_profile),
            media_type="text/plain"
        )

# ==================== HEALTH PROFILE ====================

@app.get("/api/health/profile")
async def get_health_profile(request: Request):
    """Get user's health profile"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        profile = get_or_create_health_profile(db, user_id)
        
        return {
            "profile": {
                "ayurvedic_dosha": profile.ayurvedic_dosha,
                "tcm_pattern": profile.tcm_pattern,
                "body_type": profile.body_type,
                "current_conditions": profile.current_conditions or [],
                "medications": profile.medications or [],
                "allergies": profile.allergies or [],
                "past_diagnoses": profile.past_diagnoses or [],
                "diet_type": profile.diet_type,
                "exercise_frequency": profile.exercise_frequency,
                "sleep_hours": profile.sleep_hours,
                "stress_level": profile.stress_level,
                "preferred_traditions": profile.preferred_traditions or [],
                "treatment_philosophy": profile.treatment_philosophy,
                "health_goals": profile.health_goals or []
            }
        }

@app.put("/api/health/profile")
async def update_profile(profile_update: HealthProfileUpdate, request: Request):
    """Update user's health profile"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Update only provided fields
        update_data = profile_update.dict(exclude_unset=True)
        profile = update_health_profile(db, user_id, **update_data)
        
        return {
            "message": "Profile updated successfully",
            "profile": {
                "ayurvedic_dosha": profile.ayurvedic_dosha,
                "tcm_pattern": profile.tcm_pattern,
                "body_type": profile.body_type,
                "current_conditions": profile.current_conditions or [],
                "medications": profile.medications or [],
                "preferred_traditions": profile.preferred_traditions or []
            }
        }

# ==================== SUBSCRIPTIONS & STRIPE ====================

@app.post("/api/subscription/create-checkout")
async def create_checkout_session(request: SubscriptionRequest, http_request: Request):
    """Create Stripe checkout session"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    user_id = get_current_user_id(http_request)
    
    with get_db_context() as db:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get price ID
        price_id = STRIPE_PRICES.get(request.tier)
        if not price_id or price_id == 'price_YOUR_PREMIUM_ID' or price_id == 'price_YOUR_PRO_ID':
            raise HTTPException(status_code=400, detail="Invalid tier or price not configured")
        
        try:
            # Create or get Stripe customer
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={'user_id': str(user.id)}
                )
                user.stripe_customer_id = customer.id
                db.commit()
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/subscriptions.html?success=true',
                cancel_url=os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/subscriptions.html?cancelled=true',
                metadata={
                    'user_id': str(user.id),
                    'tier': request.tier
                }
            )
            
            return {"checkout_url": checkout_session.url}
            
        except Exception as e:
            print(f"❌ Stripe error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/subscription/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        with get_db_context() as db:
            user_id = session['metadata'].get('user_id')
            user = get_user_by_id(db, user_id)
            
            if user:
                user.subscription_tier = session['metadata'].get('tier')
                user.subscription_status = 'active'
                user.stripe_subscription_id = session.get('subscription')
                
                # Set expiration to far future (recurring)
                user.subscription_expires_at = datetime.utcnow() + timedelta(days=365)
                
                db.commit()
                print(f"✅ Subscription activated for {user.email}")
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        
        with get_db_context() as db:
            # Find user by stripe subscription ID
            user = db.query(User).filter(
                User.stripe_subscription_id == subscription['id']
            ).first()
            
            if user:
                # Update subscription status
                if subscription['status'] == 'active':
                    user.subscription_status = 'active'
                elif subscription['status'] in ['canceled', 'unpaid']:
                    user.subscription_status = 'cancelled'
                
                db.commit()
                print(f"✅ Subscription updated for {user.email}")
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        
        with get_db_context() as db:
            user = db.query(User).filter(
                User.stripe_subscription_id == subscription['id']
            ).first()
            
            if user:
                user.subscription_tier = 'free'
                user.subscription_status = 'cancelled'
                user.subscription_expires_at = datetime.utcnow()
                
                db.commit()
                print(f"✅ Subscription cancelled for {user.email}")
    
    return {"status": "success"}


@app.post("/api/subscription/portal")
async def create_portal_session(request: Request):
    """Create Stripe customer portal session"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = get_user_by_id(db, user_id)
        if not user or not user.stripe_customer_id:
            raise HTTPException(status_code=404, detail="No active subscription")
        
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/settings.html',
            )
            
            return {"portal_url": portal_session.url}
            
        except Exception as e:
            print(f"❌ Stripe portal error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/subscription/cancel")
async def cancel_subscription(cancel_request: CancelSubscriptionRequest, http_request: Request):
    """Cancel subscription at period end"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    user_id = get_current_user_id(http_request)
    
    with get_db_context() as db:
        user = get_user_by_id(db, user_id)
        if not user or not user.stripe_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription")
        
        try:
            # Cancel at period end (not immediately)
            subscription = stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=True,
                metadata={'cancellation_reason': cancel_request.reason or 'User requested'}
            )
            
            user.subscription_status = 'cancelling'
            db.commit()
            
            return {
                "message": "Subscription will cancel at period end",
                "cancel_at": datetime.fromtimestamp(subscription.cancel_at).isoformat()
            }
            
        except Exception as e:
            print(f"❌ Cancellation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/subscription/status")
async def get_subscription_status(request: Request):
    """Get current subscription status"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "tier": user.subscription_tier,
            "status": user.subscription_status,
            "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "messages_this_month": user.messages_this_month or 0,
            "messages_reset_date": user.messages_reset_date.isoformat() if user.messages_reset_date else None,
            "stripe_customer_id": user.stripe_customer_id,
            "has_active_subscription": user.subscription_tier in ['premium', 'pro'] and user.subscription_status == 'active'
        }

# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
