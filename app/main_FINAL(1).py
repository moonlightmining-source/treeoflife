"""
Tree of Life AI - Complete Backend
Auth + Chat functionality with Professional Tone
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt
import uuid
import os

# Try to import anthropic - graceful fallback if not installed
try:
    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    ANTHROPIC_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Anthropic not available: {e}")
    anthropic_client = None
    ANTHROPIC_AVAILABLE = False

app = FastAPI(title="Tree of Life AI API")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory storage (replace with database later)
users = {}
conversations = {}
messages = {}
health_profiles = {}  # {email: {health_data...}}
user_settings = {}    # {email: {settings...}}

# JWT config
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

# CORS - Allow your domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://treeoflifeai.com",
        "https://www.treeoflifeai.com",
        "http://treeoflifeai.com",
        "http://www.treeoflifeai.com",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MODELS
# ============================================

# Auth Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    terms_accepted: bool

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Chat Models
class ConversationCreate(BaseModel):
    initial_message: str

class MessageCreate(BaseModel):
    content: str

# Health Profile Models
class HealthProfileUpdate(BaseModel):
    # Basic info
    age: Optional[int] = None
    sex: Optional[str] = None
    location: Optional[str] = None
    
    # Medical history
    current_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    past_diagnoses: Optional[List[str]] = []
    surgeries: Optional[List[str]] = []
    family_history: Optional[Dict[str, Any]] = {}
    
    # Constitutional types
    ayurvedic_dosha: Optional[str] = None
    tcm_constitution: Optional[str] = None
    body_type: Optional[str] = None
    
    # Lifestyle
    diet_type: Optional[str] = None
    exercise_frequency: Optional[str] = None
    exercise_types: Optional[List[str]] = []
    sleep_hours: Optional[float] = None
    stress_level: Optional[int] = None
    occupation: Optional[str] = None
    
    # Preferences
    preferred_traditions: Optional[List[str]] = []
    treatment_philosophy: Optional[str] = None
    health_goals: Optional[List[str]] = []

# ============================================
# SYSTEM PROMPTS
# ============================================

# ✅ UPDATED: More professional, less overly empathetic
SYSTEM_PROMPT_BASE = """You are Tree of Life AI, an integrative health intelligence assistant. You provide guidance from eight medical traditions:

1. Western Medicine (evidence-based, scientific)
2. Ayurveda (doshas, prakruti, lifestyle)
3. Traditional Chinese Medicine (qi, meridians, five elements)
4. Herbal Medicine (botanical therapeutics)
5. Homeopathy (like cures like, dilutions)
6. Chiropractic Principles (spinal health, alignment)
7. Clinical Nutrition (therapeutic diet, supplements)
8. Vibrational Healing (sound, light, energy work)

CORE PRINCIPLES:
- Provide EDUCATIONAL information only, never medical diagnosis
- Include perspectives from multiple traditions when relevant
- Flag emergency situations immediately
- Balance scientific evidence with traditional wisdom
- Direct users to healthcare professionals for serious concerns

COMMUNICATION STYLE:
- Professional and knowledgeable, not overly friendly
- Conversational but maintain appropriate boundaries
- Clear and direct without excessive empathy
- Focus on practical information and guidance
- Keep responses concise - get straight to the answer
- Don't repeat your introduction (user already knows who you are)

SAFETY PROTOCOLS:
- Emergency symptoms (chest pain, severe bleeding, loss of consciousness, severe allergic reaction, suicidal thoughts) → 
  "🚨 This requires immediate medical attention. Call 911 or go to the nearest emergency room now."
- Concerning symptoms → Include "when to see a doctor" guidance
- Never recommend stopping prescribed medications
- Always note potential herb-drug interactions
"""

def build_personalized_prompt(user_first_name: str, health_profile: Optional[Dict] = None) -> str:
    """Build personalized system prompt with user's name and health context"""
    
    # Start with base prompt
    prompt = SYSTEM_PROMPT_BASE
    
    # Add personalization section
    prompt += f"\n\nUSER CONTEXT:\n"
    prompt += f"- User's name: {user_first_name}\n"
    
    # Add health profile if available
    if health_profile:
        if health_profile.get('ayurvedic_dosha'):
            prompt += f"- Ayurvedic constitution: {health_profile['ayurvedic_dosha']}\n"
        if health_profile.get('tcm_constitution'):
            prompt += f"- TCM constitution: {health_profile['tcm_constitution']}\n"
        if health_profile.get('preferred_traditions'):
            traditions = ', '.join(health_profile['preferred_traditions'])
            prompt += f"- Preferred traditions: {traditions}\n"
        if health_profile.get('current_conditions'):
            conditions = ', '.join(health_profile['current_conditions'])
            prompt += f"- Current conditions: {conditions}\n"
    
    prompt += "\nAddress the user by their first name occasionally (not every message). Keep responses professional and informative."
    
    return prompt

# ============================================
# HELPER FUNCTIONS
# ============================================

def create_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(authorization: Optional[str] = Header(None)):
    """Verify JWT token from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization token provided")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def detect_emergency(text: str) -> bool:
    """Check if message contains emergency keywords"""
    emergency_keywords = [
        "chest pain", "can't breathe", "can't wake", "unconscious",
        "severe bleeding", "suicide", "kill myself", "overdose",
        "heart attack", "stroke", "severe allergic"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in emergency_keywords)

# ============================================
# AUTH ROUTES
# ============================================

@app.get("/")
def root():
    return {
        "message": "Tree of Life AI API",
        "status": "online",
        "version": "2.1.0",
        "anthropic_configured": ANTHROPIC_AVAILABLE,
        "endpoints": {
            "auth": ["/api/auth/login", "/api/auth/register"],
            "chat": ["/api/chat/conversations", "/api/chat/conversations/{id}/messages"]
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "anthropic_configured": ANTHROPIC_AVAILABLE,
        "users_count": len(users),
        "conversations_count": len(conversations)
    }

@app.post("/api/auth/register")
def register(user: UserRegister):
    try:
        print(f"📝 Register attempt: {user.email}")
        
        if not user.terms_accepted:
            raise HTTPException(status_code=400, detail="Must accept terms")
        
        if user.email in users:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        if len(user.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be 8+ characters")
        
        # Save user
        users[user.email] = {
            "email": user.email,
            "password": pwd_context.hash(user.password),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "subscription_tier": "free",
            "subscription_status": "active",
            "subscription_expires_at": None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        print(f"✅ User registered: {user.email}")
        
        return {
            "success": True,
            "token": create_token(user.email),
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login")
def login(credentials: UserLogin):
    print(f"🔐 Login attempt: {credentials.email}")
    
    user = users.get(credentials.email)
    if not user:
        print(f"❌ User not found: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not pwd_context.verify(credentials.password, user["password"]):
        print(f"❌ Invalid password for: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    print(f"✅ Login successful: {credentials.email}")
    
    return {
        "success": True,
        "token": create_token(credentials.email),
        "user": {
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"]
        }
    }

# ============================================
# CHAT ROUTES
# ============================================

@app.post("/api/chat/conversations")
async def create_conversation(
    data: ConversationCreate,
    email: str = Depends(verify_token)
):
    """Create a new conversation with initial message"""
    
    if not ANTHROPIC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please set ANTHROPIC_API_KEY environment variable."
        )
    
    try:
        print(f"💬 Creating conversation for {email}")
        
        # Get user info for personalization
        user = users.get(email)
        user_first_name = user.get("first_name", "there") if user else "there"
        
        # Get health profile if exists
        health_profile = health_profiles.get(email)
        
        # Build personalized system prompt
        system_prompt = build_personalized_prompt(user_first_name, health_profile)
        
        # Create conversation
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = {
            "id": conversation_id,
            "user_email": email,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message_count": 0
        }
        
        # Initialize message list
        messages[conversation_id] = []
        
        # Add user message
        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": data.initial_message,
            "created_at": datetime.utcnow().isoformat()
        }
        messages[conversation_id].append(user_message)
        
        # Check for emergency
        if detect_emergency(data.initial_message):
            ai_response = """🚨 MEDICAL EMERGENCY DETECTED

Based on what you've described, this could be a medical emergency.

⚠️ CALL 911 IMMEDIATELY or go to the nearest emergency room.

Do not wait. Do not try to treat this yourself. Get professional medical help right now.

This is not medical advice, but these symptoms require immediate professional evaluation."""
            print(f"🚨 Emergency detected in conversation {conversation_id}")
        else:
            # Call Claude API with personalized prompt
            print(f"🤖 Calling Claude API...")
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": data.initial_message}
                ]
            )
            
            ai_response = response.content[0].text
            print(f"✅ Claude response received ({len(ai_response)} chars)")
        
        # Add AI message
        ai_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response,
            "created_at": datetime.utcnow().isoformat()
        }
        messages[conversation_id].append(ai_message)
        
        # Update message count
        conversations[conversation_id]["message_count"] = len(messages[conversation_id])
        
        return {
            "success": True,
            "data": {
                "conversation": conversations[conversation_id],
                "message": ai_message
            }
        }
        
    except Exception as e:
        print(f"❌ Error creating conversation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@app.post("/api/chat/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    email: str = Depends(verify_token)
):
    """Send a message to existing conversation"""
    
    if not ANTHROPIC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please set ANTHROPIC_API_KEY environment variable."
        )
    
    # Check if conversation exists
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify user owns this conversation
    if conversations[conversation_id]["user_email"] != email:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    
    try:
        print(f"💬 Message in conversation {conversation_id} from {email}")
        
        # Get user info for personalization
        user = users.get(email)
        user_first_name = user.get("first_name", "there") if user else "there"
        
        # Get health profile if exists
        health_profile = health_profiles.get(email)
        
        # Build personalized system prompt
        system_prompt = build_personalized_prompt(user_first_name, health_profile)
        
        # Add user message
        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": data.content,
            "created_at": datetime.utcnow().isoformat()
        }
        messages[conversation_id].append(user_message)
        
        # Check for emergency
        if detect_emergency(data.content):
            ai_response = "🚨 MEDICAL EMERGENCY DETECTED\n\nPlease call 911 immediately or go to the nearest emergency room. Do not wait."
            print(f"🚨 Emergency detected")
        else:
            # Build message history for Claude
            claude_messages = []
            for msg in messages[conversation_id]:
                if msg["role"] in ["user", "assistant"]:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Call Claude API with personalized prompt
            print(f"🤖 Calling Claude API with {len(claude_messages)} messages...")
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=system_prompt,
                messages=claude_messages
            )
            
            ai_response = response.content[0].text
            print(f"✅ Claude response received ({len(ai_response)} chars)")
        
        # Add AI message
        ai_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response,
            "created_at": datetime.utcnow().isoformat()
        }
        messages[conversation_id].append(ai_message)
        
        # Update conversation
        conversations[conversation_id]["updated_at"] = datetime.utcnow().isoformat()
        conversations[conversation_id]["message_count"] = len(messages[conversation_id])
        
        return {
            "success": True,
            "data": {
                "message": ai_message
            }
        }
        
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@app.get("/api/chat/conversations")
def list_conversations(email: str = Depends(verify_token)):
    """List all conversations for the authenticated user"""
    user_conversations = [
        conv for conv in conversations.values()
        if conv["user_email"] == email
    ]
    
    # Sort by updated_at, newest first
    user_conversations.sort(
        key=lambda x: x["updated_at"],
        reverse=True
    )
    
    return {
        "success": True,
        "data": {
            "conversations": user_conversations,
            "total": len(user_conversations)
        }
    }

@app.get("/api/chat/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    email: str = Depends(verify_token)
):
    """Get a specific conversation with all messages"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations[conversation_id]
    
    # Verify user owns this conversation
    if conversation["user_email"] != email:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "success": True,
        "data": {
            "conversation": conversation,
            "messages": messages.get(conversation_id, [])
        }
    }

@app.delete("/api/chat/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    email: str = Depends(verify_token)
):
    """Delete a conversation"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations[conversation_id]
    
    # Verify user owns this conversation
    if conversation["user_email"] != email:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete conversation and messages
    del conversations[conversation_id]
    if conversation_id in messages:
        del messages[conversation_id]
    
    return {
        "success": True,
        "message": "Conversation deleted"
    }

# ============================================
# HEALTH PROFILE ROUTES
# ============================================

@app.get("/api/health/profile")
def get_health_profile(email: str = Depends(verify_token)):
    """Get user's health profile"""
    profile = health_profiles.get(email, {})
    return {
        "success": True,
        "data": {"profile": profile}
    }

@app.put("/api/health/profile")
def update_health_profile(
    profile_data: HealthProfileUpdate,
    email: str = Depends(verify_token)
):
    """Update user's health profile"""
    
    # Get existing profile or create new one
    profile = health_profiles.get(email, {})
    
    # Update with new data
    update_dict = profile_data.dict(exclude_unset=True)
    profile.update(update_dict)
    profile["updated_at"] = datetime.utcnow().isoformat()
    
    # Save
    health_profiles[email] = profile
    
    return {
        "success": True,
        "data": {"profile": profile}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
