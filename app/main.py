from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Boolean, Text, JSON, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from datetime import datetime, timedelta
import os
import jwt
import bcrypt
import anthropic
import stripe
import base64
import json
import asyncio
from typing import Optional, List, Dict
from app.enhanced_system_prompt import SYSTEM_PROMPT_WITH_WESTERN_MED
from app.skill_loader import get_specialized_knowledge

# Near top of main.py, after imports
MESSAGE_LIMITS = {
    'free': 10,      # 10 messages/month
    'basic': 50,     # 50 messages/month  
    'premium': 200,  # 200 messages/month
    'pro': 500       # 500 messages/month
}

# Add this helper function
def check_message_limit(user_id, tier):
    """Check if user has exceeded monthly message limit"""
    with get_db_context() as db:
        # Get message count for current month
        from datetime import datetime
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        message_count = db.query(Message).join(Conversation).filter(
            Conversation.user_id == user_id,
            Message.timestamp >= current_month_start,
            Message.role == 'user'  # Only count user messages
        ).count()
        
        limit = MESSAGE_LIMITS.get(tier, MESSAGE_LIMITS['free'])
        
        if message_count >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Monthly message limit reached ({limit} messages). Upgrade your plan for more messages."
            )

# ==================== CONFIGURATION ====================

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_PROJECT_ID = os.getenv('ANTHROPIC_PROJECT_ID')  # ← NEW: Add this to your Render environment variables
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = STRIPE_SECRET_KEY

# ==================== ANTHROPIC SETUP ====================
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ==================== STRIPE PRICE IDS ====================
STRIPE_PRICES = {
    'basic': os.getenv('STRIPE_BASIC_PRICE_ID'),
    'premium': os.getenv('STRIPE_PREMIUM_PRICE_ID'),
    'pro': os.getenv('STRIPE_PRO_PRICE_ID')
}

# ==================== DATABASE SETUP ====================

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ==================== MODELS ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    subscription_tier = Column(String, default='free')
    family_member_limit = Column(Integer, default=0)
    stripe_customer_id = Column(String)
    stripe_subscription_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    relationship = Column(String)
    age = Column(Integer)
    gender = Column(String)
    notes = Column(Text)
    date_of_birth = Column(Date)
    conversation_count = Column(Integer, default=0)
    has_health_profile = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class HealthProfile(Base):
    __tablename__ = "health_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True)
    
    # Basic Information
    full_name = Column(String)
    date_of_birth = Column(Date)
    sex = Column(String)
    blood_type = Column(String)
    height_inches = Column(Integer)
    weight = Column(Integer)
    ethnicity = Column(String)
    emergency_contact_name = Column(String)
    emergency_contact_phone = Column(String)
    
    # Alternative Medicine
    ayurvedic_dosha = Column(String)
    tcm_pattern = Column(String)
    
    # Lifestyle
    diet_type = Column(String)
    sleep_hours = Column(Float)
    stress_level = Column(Integer)
    preferred_traditions = Column(JSON)
    
    # Medical History
    current_conditions = Column(JSON)
    allergies = Column(JSON)
    past_diagnoses = Column(JSON)
    medications = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HealthMetric(Base):
    __tablename__ = "health_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    metric_type = Column(String, nullable=False)
    value = Column(String, nullable=False)
    unit = Column(String)
    notes = Column(Text)
    recorded_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Protocol(Base):
    __tablename__ = "protocols"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    traditions = Column(String)
    description = Column(Text)
    duration_weeks = Column(Integer, default=4)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProtocolPhase(Base):
    __tablename__ = "protocol_phases"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey('protocols.id'), nullable=False)
    week_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    instructions = Column(Text)
    herbs_supplements = Column(JSON)
    lifestyle_changes = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ClientProtocol(Base):
    __tablename__ = "client_protocols"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    client_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    protocol_id = Column(Integer, ForeignKey('protocols.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    current_week = Column(Integer, default=1)
    status = Column(String, default='active')
    completion_percentage = Column(Integer, default=0)
    assigned_at = Column(DateTime, default=datetime.utcnow)

class ComplianceLog(Base):
    __tablename__ = "compliance_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_protocol_id = Column(Integer, ForeignKey('client_protocols.id'), nullable=False)
    week_number = Column(Integer, nullable=False)
    compliance_score = Column(Integer)
    notes = Column(Text)
    logged_at = Column(DateTime, default=datetime.utcnow)

# ==================== DATABASE MIGRATION ====================

def run_migration():
    """Run database migration"""
    print("🔧 Running database migration...")
    
    try:
        with engine.connect() as conn:
            print("🔑 Ensuring UUID extension...")
            try:
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                conn.commit()
            except Exception as e:
                print(f"  ⚠️ UUID extension: {e}")
            
            print("👤 Checking users table columns...")
            
            try:
                conn.execute(text("""
                    ALTER TABLE users 
                    ALTER COLUMN id SET DEFAULT gen_random_uuid()
                """))
                conn.commit()
                print("  ✅ Fixed users.id UUID generation")
            except Exception as e:
                print(f"  ⚠️ users.id fix: {e}")
            
            user_migrations = [
                ("hashed_password", "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)"),
                ("full_name", "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)"),
                ("subscription_tier", "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free'"),
                ("family_member_limit", "ALTER TABLE users ADD COLUMN IF NOT EXISTS family_member_limit INTEGER DEFAULT 0"),
                ("stripe_customer_id", "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)"),
                ("stripe_subscription_id", "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)"),
                ("created_at", "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ]
            
            for col_name, query in user_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                    print(f"  ✅ Checked {col_name}")
                except Exception as e:
                    print(f"  ⚠️  {col_name}: {e}")
            
            print("✅ Users table updated!")
            
            print("👨‍👩‍👧‍👦 Checking family members fields...")
            family_migrations = [
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS age INTEGER",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS gender VARCHAR(50)",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS notes TEXT",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS conversation_count INTEGER DEFAULT 0",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS has_health_profile BOOLEAN DEFAULT FALSE"
            ]
            
            for query in family_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"  ⚠️  Family member note: {e}")
            
            print("✅ Family members fields checked!")
            
            print("🏥 Checking health profile fields...")
            health_migrations = [
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS date_of_birth DATE",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS sex VARCHAR(50)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS blood_type VARCHAR(10)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS height_inches INTEGER",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS weight INTEGER",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS ethnicity VARCHAR(100)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(255)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(20)"
            ]
            
            for query in health_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"  ⚠️  Health profile note: {e}")
            
            print("✅ Health profile fields checked!")
            
            print("👨‍👩‍👧‍👦 Fixing family_members ID auto-increment...")
            try:
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'family_members_id_seq') THEN
                            CREATE SEQUENCE family_members_id_seq;
                        END IF;
                        
                        ALTER TABLE family_members 
                        ALTER COLUMN id SET DEFAULT nextval('family_members_id_seq');
                        
                        ALTER SEQUENCE family_members_id_seq OWNED BY family_members.id;
                        
                        PERFORM setval('family_members_id_seq', COALESCE((SELECT MAX(id) FROM family_members), 0) + 1, false);
                    END $$;
                """))
                conn.commit()
                print("  ✅ Fixed family_members.id auto-increment")
            except Exception as e:
                print(f"  ⚠️ family_members.id fix: {e}")
            
            print("✅ Database migration completed!")
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        raise

# ==================== FASTAPI APP ====================
app = FastAPI(title="Tree of Life AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SYSTEM_PROMPT now imported from enhanced_system_prompt.py
# Western Medicine is always embedded; specialized skills load dynamically

# ==================== STARTUP EVENT ====================

@app.on_event("startup")
async def startup_event():
    print("🌳 Starting Tree of Life AI...")
    
    print("🔧 Checking family_members.id data type...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'family_members' 
                AND column_name = 'id'
            """))
            row = result.fetchone()
            
            if row and row[0] != 'integer':
                print(f"  ⚠️ family_members.id is {row[0]}, converting to INTEGER...")
                
                conn.execute(text("ALTER TABLE IF EXISTS client_protocols DROP CONSTRAINT IF EXISTS client_protocols_client_id_fkey CASCADE"))
                conn.commit()
                
                conn.execute(text("""
                    ALTER TABLE family_members 
                    ALTER COLUMN id TYPE INTEGER USING id::integer
                """))
                conn.commit()
                print("  ✅ Converted family_members.id to INTEGER")
            else:
                print("  ✅ family_members.id is already INTEGER")
                
    except Exception as e:
        print(f"  ⚠️ family_members.id check: {e}")
    
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
    run_migration()
    
    print("🔧 Fixing conversations table...")
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS messages CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        print("✅ Conversations table recreated")
    except Exception as e:
        print(f"⚠️ Conversations fix: {e}")
    
   # ✅ CHECK PROJECT ID AND SDK VERSION
    if ANTHROPIC_PROJECT_ID:
        print(f"✅ Claude Project ID configured: {ANTHROPIC_PROJECT_ID[:8]}...")
        print(f"📦 Anthropic SDK version: {anthropic.__version__}")
    else:
        print("⚠️ WARNING: ANTHROPIC_PROJECT_ID not set - skills will not be accessible!")
    
    print("🚀 Tree of Life AI is ready!")

# ==================== HELPER FUNCTIONS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {'user_id': str(user_id), 'exp': datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(request: Request) -> str:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth_header.split(' ')[1]
    return verify_token(token)

def get_or_create_health_profile(db, user_id):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    if not profile:
        profile = HealthProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

# ==================== AUTH ENDPOINTS ====================

class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
async def register(request: SignupRequest):
    with get_db_context() as db:
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        token = create_token(user.id)
        return {"token": token, "user": {"email": user.email, "name": user.full_name}}

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    with get_db_context() as db:
        user = db.query(User).filter(User.email == request.email).first()
        if not user or not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token(user.id)
        return {"token": token, "user": {"email": user.email, "name": user.full_name}}

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current user info"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.full_name,
            "subscription_tier": user.subscription_tier or 'free',
            "family_member_limit": user.family_member_limit or 0
        }

@app.delete("/api/auth/account")
async def delete_account(request: Request):
    """Delete user account and all associated data"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db.query(Message).filter(Message.conversation_id.in_(
            db.query(Conversation.id).filter(Conversation.user_id == user_id)
        )).delete(synchronize_session=False)
        
        db.query(Conversation).filter(Conversation.user_id == user_id).delete()
        db.query(FamilyMember).filter(FamilyMember.user_id == user_id).delete()
        db.query(HealthProfile).filter(HealthProfile.user_id == user_id).delete()
        db.query(HealthMetric).filter(HealthMetric.user_id == user_id).delete()
        
        try:
            db.execute(text("DELETE FROM lab_results WHERE user_id = :user_id"), {'user_id': str(user_id)})
        except:
            pass
        
        db.delete(user)
        db.commit()
        
        return {"success": True, "message": "Account deleted"}

# ==================== CHAT ENDPOINTS ====================

class ConversationCreate(BaseModel):
    initial_message: str
    image: Optional[Dict] = None

class MessageCreate(BaseModel):
    message: str
    image: Optional[Dict] = None

@app.post("/api/chat/conversations")
async def create_conversation_endpoint(request: Request, data: ConversationCreate):
    user_id = get_current_user_id(request)
    
    # Check message limit
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        check_message_limit(user_id, user.subscription_tier or 'free')
    
    with get_db_context() as db:
        conversation = Conversation(user_id=user_id, title=data.initial_message[:50])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        user_message = Message(
            conversation_id=conversation.id,
            role='user',
            content=data.initial_message
        )
        db.add(user_message)
        db.commit()
        
        messages = [{"role": "user", "content": data.initial_message}]
        
        if data.image:
            messages[0] = {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": data.image['type'], "data": data.image['data']}},
                    {"type": "text", "text": data.initial_message}
                ]
            }
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Load specialized skill if needed
        specialized = get_specialized_knowledge(data.initial_message)
        final_prompt = SYSTEM_PROMPT_WITH_WESTERN_MED + specialized
        
        # Enable prompt caching for cost savings
        api_params = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": [
                {
                    "type": "text",
                    "text": final_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            "messages": messages
        }
        
        response = client.messages.create(**api_params)
        
        ai_content = response.content[0].text
        
        ai_message = Message(
            conversation_id=conversation.id,
            role='assistant',
            content=ai_content
        )
        db.add(ai_message)
        db.commit()
        
        return {
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat()
            },
            "messages": [
                {"role": "user", "content": data.initial_message, "timestamp": user_message.timestamp.isoformat()},
                {"role": "assistant", "content": ai_content, "timestamp": ai_message.timestamp.isoformat()}
            ]
        }
@app.get("/api/chat/conversations")
async def get_conversations(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversations = db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).all()
        return {
            "conversations": [{
                "id": str(c.id),
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            } for c in conversations]
        }

@app.get("/api/chat/conversations/{conversation_id}")
async def get_conversation(request: Request, conversation_id: str):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()
        
        return {
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat()
            },
            "messages": [{
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat()
            } for m in messages]
        }

@app.post("/api/chat/conversations/{conversation_id}/messages")
async def send_message(request: Request, conversation_id: str, data: MessageCreate):
    user_id = get_current_user_id(request)
    
    # Check message limit
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        check_message_limit(user_id, user.subscription_tier or 'free')
    
    with get_db_context() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        user_message = Message(
            conversation_id=conversation_id,
            role='user',
            content=data.message
        )
        db.add(user_message)
        db.commit()
        
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()
        
        claude_messages = []
        for msg in messages:
            claude_messages.append({"role": msg.role, "content": msg.content})
        
        if data.image:
            claude_messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": data.image['type'], "data": data.image['data']}},
                    {"type": "text", "text": data.message}
                ]
            }
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Load specialized skill if needed
        specialized = get_specialized_knowledge(data.message)
        final_prompt = SYSTEM_PROMPT_WITH_WESTERN_MED + specialized
        
        # Enable prompt caching
        api_params = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": [
                {
                    "type": "text",
                    "text": final_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            "messages": claude_messages
        }
        
        response = client.messages.create(**api_params)
        
        ai_content = response.content[0].text
        
        ai_message = Message(
            conversation_id=conversation_id,
            role='assistant',
            content=ai_content
        )
        db.add(ai_message)
        db.commit()
        
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "message": {
                "role": "assistant",
                "content": ai_content,
                "timestamp": ai_message.timestamp.isoformat()
            }
        }

       
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        db.delete(conversation)
        db.commit()
        
        return {"success": True}

@app.delete("/api/chat/conversations/{conversation_id}")
async def delete_conversation(request: Request, conversation_id: str):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        db.delete(conversation)
        db.commit()
        
        return {"success": True}

# ==================== FAMILY MEMBER ENDPOINTS ====================

class FamilyMemberCreate(BaseModel):
    name: str
    relationship: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    date_of_birth: Optional[str] = None

@app.get("/api/family/members")
async def get_family_members(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        members = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).all()
        return {"members": [{
            "id": str(m.id),
            "name": m.name,
            "relationship": m.relationship,
            "age": m.age,
            "gender": m.gender,
            "notes": m.notes,
            "date_of_birth": m.date_of_birth.isoformat() if m.date_of_birth else None,
            "conversation_count": m.conversation_count or 0,
            "has_health_profile": m.has_health_profile or False
        } for m in members]}

@app.post("/api/family/members")
async def create_family_member(request: Request, member: FamilyMemberCreate):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        count = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).count()
        
        if count >= user.family_member_limit:
            raise HTTPException(status_code=403, detail="Family member limit reached")
        
        new_member = FamilyMember(
            user_id=user_id,
            name=member.name,
            relationship=member.relationship,
            age=member.age,
            gender=member.gender,
            notes=member.notes,
            date_of_birth=member.date_of_birth if member.date_of_birth else None
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        
        return {"id": new_member.id, "name": new_member.name}

@app.put("/api/family/members/{member_id}")
async def update_family_member(request: Request, member_id: int, member: FamilyMemberCreate):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        existing = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Member not found")
        
        existing.name = member.name
        existing.relationship = member.relationship
        existing.age = member.age
        existing.gender = member.gender
        existing.notes = member.notes
        if member.date_of_birth:
            existing.date_of_birth = member.date_of_birth
        
        db.commit()
        return {"success": True}

@app.delete("/api/family/members/{member_id}")
async def delete_family_member(request: Request, member_id: int):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        db.delete(member)
        db.commit()
        
        return {"success": True}

# ==================== SUBSCRIPTION ENDPOINTS ====================

@app.get("/api/subscription/status")
async def get_subscription_status(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "tier": user.subscription_tier or 'free',
            "family_member_limit": user.family_member_limit or 0,
            "messages_this_month": 0
        }

@app.post("/api/subscription/create-checkout")
async def create_checkout_session(request: Request):
    user_id = get_current_user_id(request)
    data = await request.json()
    tier = data.get('tier')
    
    if tier not in STRIPE_PRICES:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    price_id = STRIPE_PRICES[tier]
    if not price_id:
        raise HTTPException(status_code=500, detail=f"Stripe price not configured for {tier}")
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={'user_id': str(user.id)}
            )
            user.stripe_customer_id = customer.id
            db.commit()
        
        try:
            checkout_session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url='https://treeoflifeai.com/subscriptions.html?success=true',
                cancel_url='https://treeoflifeai.com/index.html',
                client_reference_id=str(user.id),
                metadata={'user_id': str(user.id), 'tier': tier}
            )
            
            return {"checkout_url": checkout_session.url}
        
        except Exception as e:
            print(f"❌ Stripe error: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

@app.post("/api/subscription/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        tier = session.get('metadata', {}).get('tier')
        subscription_id = session.get('subscription')
        
        if user_id and tier:
            with get_db_context() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.subscription_tier = tier
                    user.stripe_subscription_id = subscription_id
                    
                    if tier == 'basic':
                        user.family_member_limit = 1
                    elif tier == 'premium':
                        user.family_member_limit = 5
                    elif tier == 'pro':
                        user.family_member_limit = 999
                    
                    db.commit()
    
    return {"status": "success"}

@app.post("/api/subscription/portal")
async def create_portal_session(request: Request):
    """Create Stripe customer portal session"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No Stripe customer found")
        
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url='https://treeoflifeai.com/index.html'
            )
            
            return {"portal_url": portal_session.url}
        
        except Exception as e:
            print(f"❌ Stripe portal error: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

# ==================== HEALTH PROFILE ENDPOINTS ====================

@app.get("/api/health/profile")
async def get_health_profile(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        profile = get_or_create_health_profile(db, user_id)
        
        age = None
        if profile.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - profile.date_of_birth.year
            if (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day):
                age -= 1
        
        return {
            "profile": {
                "full_name": profile.full_name,
                "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                "age": age,
                "sex": profile.sex,
                "blood_type": profile.blood_type,
                "height_inches": profile.height_inches,
                "weight": profile.weight,
                "ethnicity": profile.ethnicity,
                "emergency_contact_name": profile.emergency_contact_name,
                "emergency_contact_phone": profile.emergency_contact_phone,
                "ayurvedic_dosha": profile.ayurvedic_dosha,
                "tcm_pattern": profile.tcm_pattern,
                "diet_type": profile.diet_type,
                "sleep_hours": profile.sleep_hours,
                "stress_level": profile.stress_level,
                "preferred_traditions": profile.preferred_traditions or [],
                "current_conditions": profile.current_conditions or [],
                "allergies": profile.allergies or [],
                "past_diagnoses": profile.past_diagnoses or [],
                "medications": profile.medications or []
            }
        }

@app.put("/api/health/profile")
async def update_health_profile(request: Request):
    user_id = get_current_user_id(request)
    data = await request.json()
    
    with get_db_context() as db:
        profile = get_or_create_health_profile(db, user_id)
        
        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.utcnow()
        db.commit()
        
        return {"success": True}

# ==================== HEALTH METRICS ENDPOINTS ====================

class HealthMetricCreate(BaseModel):
    metric_type: str
    value: str
    unit: Optional[str] = None
    notes: Optional[str] = None
    recorded_at: str

@app.post("/api/health/metrics")
async def create_health_metric(request: Request, metric: HealthMetricCreate):
    """Create a new health metric entry"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        new_metric = HealthMetric(
            user_id=user_id,
            metric_type=metric.metric_type,
            value=metric.value,
            unit=metric.unit,
            notes=metric.notes,
            recorded_at=datetime.fromisoformat(metric.recorded_at.replace('Z', '+00:00'))
        )
        db.add(new_metric)
        db.commit()
        db.refresh(new_metric)
        
        return {
            "id": new_metric.id,
            "metric_type": new_metric.metric_type,
            "value": new_metric.value,
            "unit": new_metric.unit,
            "notes": new_metric.notes,
            "recorded_at": new_metric.recorded_at.isoformat()
        }

@app.get("/api/health/metrics")
async def get_health_metrics(
    request: Request,
    metric_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get health metrics with optional filtering"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        query = db.query(HealthMetric).filter(HealthMetric.user_id == user_id)
        
        if metric_type:
            query = query.filter(HealthMetric.metric_type == metric_type)
        
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(HealthMetric.recorded_at >= start)
        
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(HealthMetric.recorded_at <= end)
        
        metrics = query.order_by(HealthMetric.recorded_at.desc()).all()
        
        return {
            "metrics": [{
                "id": m.id,
                "metric_type": m.metric_type,
                "value": m.value,
                "unit": m.unit,
                "notes": m.notes,
                "recorded_at": m.recorded_at.isoformat(),
                "created_at": m.created_at.isoformat()
            } for m in metrics]
        }

@app.delete("/api/health/metrics/{metric_id}")
async def delete_health_metric(request: Request, metric_id: int):
    """Delete a health metric entry"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        metric = db.query(HealthMetric).filter(
            HealthMetric.id == metric_id,
            HealthMetric.user_id == user_id
        ).first()
        
        if not metric:
            raise HTTPException(status_code=404, detail="Metric not found")
        
        db.delete(metric)
        db.commit()
        
        return {"success": True}

# ==================== AI HEALTH ANALYSIS HELPERS ====================

def _format_metric_trend(metrics):
    """Format metrics for prompt"""
    if not metrics or len(metrics) == 0:
        return "No data available"
    
    recent = metrics[-5:]
    values = [f"{m.get('value')} {m.get('unit')} on {m.get('recorded_at')[:10]}" for m in recent]
    return ", ".join(values)

def _format_lab_results(lab_results):
    """Format lab results for prompt"""
    if not lab_results:
        return "No recent lab results"
    
    formatted = []
    for result in lab_results:
        formatted.append(f"\n{result.get('test_type')} - {result.get('test_date')[:10]} ({result.get('provider')})")
        for val in result.get('results', []):
            formatted.append(f"  - {val.get('name')}: {val.get('value')} {val.get('unit')} (Range: {val.get('reference_range')})")
    
    return "\n".join(formatted)

def _parse_analysis_sections(analysis_text):
    """Parse Claude's response into structured sections"""
    sections = {
        "overall_assessment": "",
        "lab_results_analysis": "",
        "metrics_trends": "",
        "medication_review": "",
        "integrative_recommendations": "",
        "lifestyle_suggestions": "",
        "western_medicine": "",
        "clinical_nutrition": "",
        "herbal_medicine": "",
        "supplement_recommendations": "",
        "ayurvedic_perspective": "",
        "tcm_perspective": "",
        "action_items": ""
    }
    
    current_section = "overall_assessment"
    lines = analysis_text.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        
        if 'overall health' in line_lower or 'health assessment' in line_lower:
            current_section = "overall_assessment"
        elif 'lab result' in line_lower:
            current_section = "lab_results_analysis"
        elif 'metric' in line_lower and 'trend' in line_lower:
            current_section = "metrics_trends"
        elif 'medication' in line_lower:
            current_section = "medication_review"
        elif 'integrative' in line_lower:
            current_section = "integrative_recommendations"
        elif 'lifestyle' in line_lower:
            current_section = "lifestyle_suggestions"
        elif 'western medicine' in line_lower:
            current_section = "western_medicine"
        elif 'clinical nutrition' in line_lower or 'nutrition' in line_lower:
            current_section = "clinical_nutrition"
        elif 'herbal medicine' in line_lower or 'herbal' in line_lower:
            current_section = "herbal_medicine"
        elif 'supplement' in line_lower:
            current_section = "supplement_recommendations"
        elif 'ayurvedic' in line_lower:
            current_section = "ayurvedic_perspective"
        elif 'tcm' in line_lower or 'chinese medicine' in line_lower:
            current_section = "tcm_perspective"
        elif 'action item' in line_lower:
            current_section = "action_items"
        else:
            sections[current_section] += line + "\n"
    
    return sections

# ==================== AI HEALTH ANALYSIS ENDPOINTS ====================

@app.post("/api/health/ai-analysis")
async def ai_health_analysis(health_data: dict, request: Request):
    """Generate comprehensive AI health analysis"""
    user_id = get_current_user_id(request)
    
    try:
        prompt = f"""You are an expert integrative health advisor with deep knowledge of Western medicine, Ayurveda, 
Traditional Chinese Medicine, Clinical Nutrition, Herbal Medicine, and evidence-based supplement therapy. 
Analyze the following health data and provide a comprehensive, personalized health assessment.

PATIENT PROFILE:
- Name: {health_data.get('personal', {}).get('name', 'User')}
- Age: {health_data.get('personal', {}).get('age', 'Not provided')}
- Sex: {health_data.get('personal', {}).get('sex', 'Not provided')}
- Blood Type: {health_data.get('personal', {}).get('blood_type', 'Not provided')}
- Height: {health_data.get('personal', {}).get('height', 'Not provided')}
- Weight: {health_data.get('personal', {}).get('weight', 'Not provided')} lbs
- Ethnicity: {health_data.get('personal', {}).get('ethnicity', 'Not provided')}

ALTERNATIVE MEDICINE PROFILE:
- Ayurvedic Dosha: {health_data.get('personal', {}).get('ayurvedic_dosha', 'Not provided')}
- TCM Pattern: {health_data.get('personal', {}).get('tcm_pattern', 'Not provided')}
- Preferred Healing Traditions: {', '.join(health_data.get('personal', {}).get('preferred_traditions', [])) or 'Not provided'}

LIFESTYLE:
- Diet Type: {health_data.get('personal', {}).get('diet_type', 'Not provided')}
- Sleep Hours: {health_data.get('personal', {}).get('sleep_hours', 'Not provided')} hours/night
- Stress Level: {health_data.get('personal', {}).get('stress_level', 'Not provided')}/10

MEDICAL HISTORY:
- Current Conditions: {', '.join(health_data.get('medical', {}).get('current_conditions', [])) or 'None reported'}
- Allergies: {', '.join(health_data.get('medical', {}).get('allergies', [])) or 'None reported'}
- Past Diagnoses: {len(health_data.get('medical', {}).get('past_diagnoses', []))} conditions
- Current Medications: {len(health_data.get('medical', {}).get('medications', []))} medications

MEDICATIONS:
{chr(10).join([f"- {med.get('name')}: {med.get('dosage')} {med.get('frequency')} ({med.get('type')})" 
               for med in health_data.get('medical', {}).get('medications', [])]) or 'None'}

RECENT HEALTH METRICS:
Weight Trend: {_format_metric_trend(health_data.get('metrics', {}).get('weight', []))}
Blood Pressure Trend: {_format_metric_trend(health_data.get('metrics', {}).get('blood_pressure', []))}
Blood Sugar Trend: {_format_metric_trend(health_data.get('metrics', {}).get('blood_sugar', []))}

RECENT LAB RESULTS:
{_format_lab_results(health_data.get('lab_results', []))}

Please provide a comprehensive health analysis with the following sections:

1. **Overall Health Assessment**: General health status and key observations
2. **Lab Results Analysis**: Interpretation of recent lab values, highlighting abnormalities
3. **Metrics Trends**: Analysis of weight, blood pressure, blood sugar trends
4. **Medication Review**: Assessment of current medications and potential interactions
5. **Integrative Recommendations**: Combine insights from multiple healing traditions
6. **Lifestyle Suggestions**: Diet, exercise, sleep, stress management recommendations
7. **Western Medicine Perspective**: Evidence-based medical insights
8. **Clinical Nutrition**: Specific nutritional therapy recommendations
9. **Herbal Medicine**: Evidence-based herbal remedies
10. **Supplement Recommendations**: Specific supplements with dosages
11. **Ayurvedic Perspective**: Recommendations based on dosha (if applicable)
12. **TCM Perspective**: Recommendations based on pattern (if applicable)
13. **Action Items**: Specific, actionable steps

Use markdown formatting. Be compassionate, clear, and actionable."""

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Always load Functional Medicine for comprehensive analysis
        specialized = get_specialized_knowledge("functional medicine comprehensive health analysis")
        final_prompt = SYSTEM_PROMPT_WITH_WESTERN_MED + specialized
        
        # Enable prompt caching
        api_params = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "system": [
                {
                    "type": "text",
                    "text": final_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            "messages": [{"role": "user", "content": prompt}]
        }
        
        message = client.messages.create(**api_params)
        
        analysis_text = message.content[0].text
        sections = _parse_analysis_sections(analysis_text)
        
        return JSONResponse(content=sections)
    
    except Exception as e:
        print(f"❌ AI analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="AI analysis failed")
@app.post("/api/health/explain-value")
async def explain_lab_value(request_data: dict, request: Request):
    """Get AI explanation for a specific lab value"""
    user_id = get_current_user_id(request)
    
    try:
        value_name = request_data.get('value_name')
        value = request_data.get('value')
        unit = request_data.get('unit')
        reference_range = request_data.get('reference_range')
        user_data = request_data.get('user_data', {})
        
        prompt = f"""Explain the following lab value in a clear, compassionate way:

Test: {value_name}
Patient's Value: {value} {unit}
Reference Range: {reference_range}

Patient Context:
- Age: {user_data.get('age', 'Not provided')}
- Sex: {user_data.get('sex', 'Not provided')}
- Current Conditions: {', '.join(user_data.get('conditions', [])) or 'None reported'}
- Current Medications: {len(user_data.get('medications', []))} medications

Please explain:
1. What this test measures
2. What the value means (is it normal, high, or low?)
3. Possible causes if abnormal
4. Health implications
5. Lifestyle factors that may affect it
6. Nutritional/supplement interventions that may help
7. When to see a doctor
8. Questions to ask your doctor

Use simple language that a non-medical person can understand."""
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Load functional medicine for lab analysis
        specialized = get_specialized_knowledge(f"{value_name} lab test functional medicine")
        final_prompt = SYSTEM_PROMPT_WITH_WESTERN_MED + specialized
        
        # Enable prompt caching
        api_params = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": [
                {
                    "type": "text",
                    "text": final_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            "messages": [{"role": "user", "content": prompt}]
        }
        
        message = client.messages.create(**api_params)
        
        explanation = message.content[0].text
        
        return JSONResponse(content={
            "explanation": explanation,
            "value_name": value_name,
            "value": value,
            "unit": unit,
            "reference_range": reference_range
        })
    
    except Exception as e:
        print(f"❌ Value explanation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Explanation failed")

# ==================== LAB RESULTS UPLOAD ENDPOINT ====================

@app.post("/api/lab-results/upload")
async def upload_lab_result(
    request: Request,
    file: UploadFile = File(...),
    provider: str = Form(...),
    test_date: str = Form(...)
):
    """Upload and extract lab results from image or PDF"""
    user_id = get_current_user_id(request)
    
    allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload JPG, PNG, or PDF only."
        )
    
    file_content = await file.read()
    
    max_size = 10 * 1024 * 1024
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )
    
    print(f"📄 Processing lab results upload: {file.filename} ({len(file_content)} bytes)")
    
    try:
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        media_type = file.content_type
        if file.filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif file.filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif file.filename.lower().endswith('.png'):
            media_type = "image/png"
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        if media_type == "application/pdf":
            content_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_content
                }
            }
        else:
            content_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_content
                }
            }
        
        extraction_prompt = """You are a medical lab results extraction expert. Extract ALL lab test values from this document.

CRITICAL INSTRUCTIONS:
1. Extract EVERY test result you can find
2. For EACH test, provide ALL four fields: name, value, unit, reference_range
3. Return ONLY valid JSON - no markdown, no explanations

REQUIRED JSON FORMAT:
{
  "test_type": "Name of the lab panel",
  "results": [
    {
      "name": "TEST NAME",
      "value": "NUMERIC VALUE ONLY",
      "unit": "UNIT",
      "reference_range": "RANGE"
    }
  ]
}

Now extract all lab values from this document:"""
        
      # Use Western Med only for extraction (no specialized skill needed)
        api_params = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 3000,
            "temperature": 0,
            "system": [
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT_WITH_WESTERN_MED,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            "messages": [{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": extraction_prompt}
                ]
            }]
        }
        
        if ANTHROPIC_PROJECT_ID:
            try:
                api_params["project_id"] = ANTHROPIC_PROJECT_ID
                message = client.messages.create(**api_params)
            except TypeError as e:
                if "project_id" in str(e):
                    del api_params["project_id"]
                    message = client.messages.create(**api_params)
                else:
                    raise
        else:
            message = client.messages.create(**api_params)
        
        response_text = message.content[0].text
        print(f"🤖 Raw AI Response:\n{response_text}\n")
        
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        response_text = response_text.strip()
        
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse extracted data. Please try uploading a clearer image."
            )
        
        if not isinstance(extracted_data, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid extraction format. Please try again."
            )
        
        if 'results' not in extracted_data:
            extracted_data['results'] = []
        
        if not isinstance(extracted_data['results'], list):
            extracted_data['results'] = []
        
        validated_results = []
        for result in extracted_data.get('results', []):
            if isinstance(result, dict):
                validated_result = {
                    'name': result.get('name', '').strip() or 'Unknown Test',
                    'value': result.get('value', '').strip() or '0',
                    'unit': result.get('unit', '').strip() or '',
                    'reference_range': result.get('reference_range', '').strip() or 'N/A'
                }
                validated_results.append(validated_result)
        
        extracted_data['results'] = validated_results
        extracted_data['provider'] = provider
        extracted_data['test_date'] = test_date
        extracted_data['file_url'] = f"uploaded/{file.filename}"
        
        if 'test_type' not in extracted_data or not extracted_data['test_type']:
            extracted_data['test_type'] = 'Lab Results'
        
        print(f"✅ Successfully extracted {len(validated_results)} lab values")
        
        return extracted_data
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"❌ Lab extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process lab results: {str(e)}"
        )

@app.post("/api/lab-results/save")
async def save_lab_results(request: Request):
    user_id = get_current_user_id(request)
    data = await request.json()
    
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lab_results (
                id SERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                test_type VARCHAR(255),
                test_date DATE,
                provider VARCHAR(255),
                file_url TEXT,
                results JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        
        try:
            conn.execute(text("""
                ALTER TABLE lab_results 
                ADD COLUMN IF NOT EXISTS file_url TEXT
            """))
            conn.commit()
        except Exception as e:
            print(f"⚠️ Column add note: {e}")
        
        conn.execute(text("""
            INSERT INTO lab_results (user_id, test_type, test_date, provider, file_url, results)
            VALUES (:user_id, :test_type, :test_date, :provider, :file_url, :results)
        """), {
            'user_id': str(user_id),
            'test_type': data.get('test_type'),
            'test_date': data.get('test_date'),
            'provider': data.get('provider'),
            'file_url': data.get('file_url'),
            'results': json.dumps(data.get('results', []))
        })
        conn.commit()
    
    return {"success": True}

@app.get("/api/lab-results")
async def get_lab_results(request: Request):
    user_id = get_current_user_id(request)
    
    with engine.connect() as conn:
        results = conn.execute(text("""
            SELECT id, test_type, test_date, provider, results, created_at
            FROM lab_results
            WHERE user_id = :user_id
            ORDER BY test_date DESC
        """), {'user_id': str(user_id)})
        
        return [{
            'id': row[0],
            'test_type': row[1],
            'test_date': row[2].isoformat() if row[2] else None,
            'provider': row[3],
            'results': row[4] if isinstance(row[4], list) else json.loads(row[4]) if row[4] else [],
            'created_at': row[5].isoformat() if row[5] else None
        } for row in results]

@app.delete("/api/lab-results/{result_id}")
async def delete_lab_result(request: Request, result_id: int):
    user_id = get_current_user_id(request)
    
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM lab_results
            WHERE id = :id AND user_id = :user_id
        """), {'id': result_id, 'user_id': str(user_id)})
        conn.commit()
    
    return {"success": True}

# ==================== PRO PROTOCOL ENDPOINTS ====================

class ProtocolCreate(BaseModel):
    name: str
    traditions: Optional[str] = None
    description: Optional[str] = None
    duration_weeks: int = 4

class PhaseCreate(BaseModel):
    week_number: int
    title: str
    instructions: Optional[str] = None
    herbs_supplements: Optional[List[Dict]] = []
    lifestyle_changes: Optional[List[str]] = []

class ProtocolAssign(BaseModel):
    client_id: int
    start_date: str

class ComplianceCreate(BaseModel):
    client_protocol_id: int
    week_number: int
    compliance_score: int
    notes: Optional[str] = None

@app.get("/api/protocols")
async def get_protocols(request: Request):
    """Get all protocols for current user"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        protocols = db.query(Protocol).filter(
            Protocol.user_id == user_id,
            Protocol.is_active == True
        ).all()
        
        return {"protocols": [{
            "id": p.id,
            "name": p.name,
            "traditions": p.traditions,
            "description": p.description,
            "duration_weeks": p.duration_weeks,
            "created_at": p.created_at.isoformat()
        } for p in protocols]}

@app.post("/api/protocols")
async def create_protocol(request: Request, protocol: ProtocolCreate):
    """Create a new protocol"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        new_protocol = Protocol(
            user_id=user_id,
            name=protocol.name,
            traditions=protocol.traditions,
            description=protocol.description,
            duration_weeks=protocol.duration_weeks
        )
        db.add(new_protocol)
        db.commit()
        db.refresh(new_protocol)
        
        return {"id": new_protocol.id, "name": new_protocol.name}

@app.put("/api/protocols/{protocol_id}")
async def update_protocol(request: Request, protocol_id: int, protocol: ProtocolCreate):
    """Update a protocol"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        existing = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        existing.name = protocol.name
        existing.traditions = protocol.traditions
        existing.description = protocol.description
        existing.duration_weeks = protocol.duration_weeks
        existing.updated_at = datetime.utcnow()
        
        db.commit()
        return {"success": True}

@app.delete("/api/protocols/{protocol_id}")
async def delete_protocol(request: Request, protocol_id: int):
    """Soft delete a protocol"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        protocol = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        protocol.is_active = False
        db.commit()
        
        return {"success": True}

@app.get("/api/protocols/{protocol_id}/phases")
async def get_protocol_phases(request: Request, protocol_id: int):
    """Get all phases for a protocol"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        protocol = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        phases = db.query(ProtocolPhase).filter(
            ProtocolPhase.protocol_id == protocol_id
        ).order_by(ProtocolPhase.week_number).all()
        
        return {"phases": [{
            "id": p.id,
            "week_number": p.week_number,
            "title": p.title,
            "instructions": p.instructions,
            "herbs_supplements": p.herbs_supplements or [],
            "lifestyle_changes": p.lifestyle_changes or []
        } for p in phases]}

@app.post("/api/protocols/{protocol_id}/phases")
async def create_phase(request: Request, protocol_id: int, phase: PhaseCreate):
    """Add a phase to a protocol"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        protocol = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        new_phase = ProtocolPhase(
            protocol_id=protocol_id,
            week_number=phase.week_number,
            title=phase.title,
            instructions=phase.instructions,
            herbs_supplements=phase.herbs_supplements,
            lifestyle_changes=phase.lifestyle_changes
        )
        db.add(new_phase)
        db.commit()
        db.refresh(new_phase)
        
        return {"id": new_phase.id}

@app.delete("/api/protocols/{protocol_id}/phases/{phase_id}")
async def delete_phase(request: Request, protocol_id: int, phase_id: int):
    """Delete a phase"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        protocol = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        phase = db.query(ProtocolPhase).filter(
            ProtocolPhase.id == phase_id,
            ProtocolPhase.protocol_id == protocol_id
        ).first()
        
        if not phase:
            raise HTTPException(status_code=404, detail="Phase not found")
        
        db.delete(phase)
        db.commit()
        
        return {"success": True}

@app.post("/api/protocols/{protocol_id}/assign")
async def assign_protocol(request: Request, protocol_id: int, assignment: ProtocolAssign):
    """Assign a protocol to a client"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        protocol = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        client = db.query(FamilyMember).filter(
            FamilyMember.id == assignment.client_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        new_assignment = ClientProtocol(
            user_id=user_id,
            client_id=assignment.client_id,
            protocol_id=protocol_id,
            start_date=datetime.fromisoformat(assignment.start_date).date()
        )
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        
        return {"id": new_assignment.id}

@app.get("/api/client-protocols")
async def get_client_protocols(request: Request):
    """Get all assigned protocols"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        assignments = db.query(ClientProtocol).filter(
            ClientProtocol.user_id == user_id
        ).all()
        
        result = []
        for a in assignments:
            client = db.query(FamilyMember).filter(FamilyMember.id == a.client_id).first()
            protocol = db.query(Protocol).filter(Protocol.id == a.protocol_id).first()
            
            result.append({
                "id": a.id,
                "client_name": client.name if client else "Unknown",
                "client_id": a.client_id,
                "protocol_name": protocol.name if protocol else "Unknown",
                "protocol_id": a.protocol_id,
                "start_date": a.start_date.isoformat(),
                "current_week": a.current_week,
                "status": a.status,
                "completion_percentage": a.completion_percentage
            })
        
        return {"assignments": result}

@app.post("/api/compliance")
async def log_compliance(request: Request, compliance: ComplianceCreate):
    """Log client compliance"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.id == compliance.client_protocol_id,
            ClientProtocol.user_id == user_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        log = ComplianceLog(
            client_protocol_id=compliance.client_protocol_id,
            week_number=compliance.week_number,
            compliance_score=compliance.compliance_score,
            notes=compliance.notes
        )
        db.add(log)
        
        assignment.current_week = compliance.week_number
        assignment.completion_percentage = min(100, (compliance.week_number /
            db.query(Protocol).filter(Protocol.id == assignment.protocol_id).first().duration_weeks) * 100)
        
        db.commit()
        
        return {"success": True}

@app.get("/api/compliance/{client_protocol_id}")
async def get_compliance(request: Request, client_protocol_id: int):
    """Get compliance logs for an assignment"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.id == client_protocol_id,
            ClientProtocol.user_id == user_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        logs = db.query(ComplianceLog).filter(
            ComplianceLog.client_protocol_id == client_protocol_id
        ).order_by(ComplianceLog.week_number).all()
        
        return {"logs": [{
            "week_number": log.week_number,
            "compliance_score": log.compliance_score,
            "notes": log.notes,
            "logged_at": log.logged_at.isoformat()
        } for log in logs]}

@app.get("/api/analytics/dashboard")
async def get_analytics(request: Request):
    """Get analytics data for dashboard"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        total_clients = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).count()
        
        active_assignments = db.query(ClientProtocol).filter(
            ClientProtocol.user_id == user_id,
            ClientProtocol.status == 'active'
        ).count()
        
        all_assignments = db.query(ClientProtocol).filter(
            ClientProtocol.user_id == user_id
        ).all()
        
        avg_completion = sum(a.completion_percentage for a in all_assignments) / len(all_assignments) if all_assignments else 0
        
        recent_logs = db.query(ComplianceLog).join(ClientProtocol).filter(
            ClientProtocol.user_id == user_id
        ).order_by(ComplianceLog.logged_at.desc()).limit(10).all()
        
        avg_compliance = sum(log.compliance_score for log in recent_logs) / len(recent_logs) if recent_logs else 0
        
        return {
            "total_clients": total_clients,
            "active_protocols": active_assignments,
            "avg_completion": round(avg_completion, 1),
            "avg_compliance": round(avg_compliance, 1),
            "client_retention": 92,
            "recent_compliance": [{
                "week": log.week_number,
                "score": log.compliance_score
            } for log in recent_logs]
        }

# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Tree of Life AI API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
