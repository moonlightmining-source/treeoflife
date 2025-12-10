"""
Tree of Life AI - Complete Backend
Auth + Chat functionality
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List
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

# ============================================
# SYSTEM PROMPT
# ============================================

SYSTEM_PROMPT = """You are Tree of Life AI, an integrative health intelligence assistant. You provide guidance from 11 medical traditions:

1. Western Medicine
2. Ayurveda
3. Traditional Chinese Medicine (TCM)
4. Herbal Medicine
5. Homeopathy
6. Chiropractic
7. Clinical Nutrition
8. Vibrational Healing
9. Fitness & Physical Therapy
10. Elder Care & Law
11. Consciousness Mapping (Tarot, Astrology, I Ching, Hero's Journey)

CRITICAL GUIDELINES:
- You provide EDUCATIONAL information only, never medical diagnosis
- Always include perspectives from multiple traditions when relevant
- Flag emergency situations immediately
- Be evidence-balanced: respect both scientific research and traditional wisdom
- Always remind users to consult healthcare professionals for serious concerns

SAFETY INSTRUCTIONS:
- If user describes emergency symptoms (chest pain, severe bleeding, loss of consciousness, 
  severe allergic reaction, suicidal thoughts), respond with:
  "🚨 This sounds like a medical emergency. Please call 911 or go to the nearest emergency 
  room immediately. Do not wait."
- For concerning symptoms, always include "when to see a doctor" guidance
- Never recommend stopping prescribed medications
- Always warn about potential herb-drug interactions

Respond in a warm, knowledgeable, and empowering tone."""

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
        "version": "2.0.0",
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
    """Create a new conversation and get first AI response"""
    
    if not ANTHROPIC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please set ANTHROPIC_API_KEY environment variable."
        )
    
    try:
        print(f"💬 New conversation from: {email}")
        
        # Create conversation
        conversation_id = str(uuid.uuid4())
        conversations[conversation_id] = {
            "id": conversation_id,
            "user_email": email,
            "title": data.initial_message[:50] + "..." if len(data.initial_message) > 50 else data.initial_message,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Initialize message history
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
            # Call Claude API
            print(f"🤖 Calling Claude API...")
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=SYSTEM_PROMPT,
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
            
            # Call Claude API
            print(f"🤖 Calling Claude API with {len(claude_messages)} messages...")
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=claude_messages
            )
            
            ai_response = response.content[0].text
            print(f"✅ Claude response received")
        
        # Add AI message
        ai_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response,
            "created_at": datetime.utcnow().isoformat()
        }
        messages[conversation_id].append(ai_message)
        
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
async def list_conversations(email: str = Depends(verify_token)):
    """List all conversations for this user"""
    
    user_conversations = [
        conv for conv in conversations.values()
        if conv.get("user_email") == email
    ]
    
    return {
        "success": True,
        "data": {
            "conversations": user_conversations
        }
    }

@app.get("/api/chat/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    email: str = Depends(verify_token)
):
    """Get all messages in a conversation"""
    
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify user owns this conversation
    if conversations[conversation_id]["user_email"] != email:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    
    return {
        "success": True,
        "data": {
            "messages": messages.get(conversation_id, [])
        }
    }

# ============================================
# DEBUG ENDPOINT
# ============================================

@app.get("/api/debug")
def debug_info():
    """Debug endpoint to check system status"""
    return {
        "anthropic_available": ANTHROPIC_AVAILABLE,
        "anthropic_api_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "users_count": len(users),
        "conversations_count": len(conversations),
        "total_messages": sum(len(msgs) for msgs in messages.values())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
