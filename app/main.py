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

# ==================== CONFIGURATION ====================

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
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
    metric_type = Column(String, nullable=False)  # 'weight', 'blood_pressure', 'blood_sugar'
    value = Column(String, nullable=False)  # Store as string to handle BP (e.g., "120/80")
    unit = Column(String)  # 'lbs', 'kg', 'mmHg', 'mg/dL'
    notes = Column(Text)
    recorded_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==================== DATABASE MIGRATION ====================

def run_migration():
    """Run database migration"""
    print("🔧 Running database migration...")
    
    try:
        with engine.connect() as conn:
            # FIX: Ensure UUID generation is enabled
            print("🔑 Ensuring UUID extension...")
            try:
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                conn.commit()
            except Exception as e:
                print(f"  ⚠️ UUID extension: {e}")
            
            # Users table
            print("👤 Checking users table columns...")
            
            # FIX: Ensure id column has UUID generation
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
            
            # Family members table
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
            
            # Health profiles table
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
            
            # FIX: Ensure family_members.id auto-increments
            print("👨‍👩‍👧‍👦 Fixing family_members ID auto-increment...")
            try:
                conn.execute(text("""
                    DO $$ 
                    BEGIN
                        -- Create a sequence if it doesn't exist
                        IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'family_members_id_seq') THEN
                            CREATE SEQUENCE family_members_id_seq;
                        END IF;
                        
                        -- Set the id column to use the sequence
                        ALTER TABLE family_members 
                        ALTER COLUMN id SET DEFAULT nextval('family_members_id_seq');
                        
                        -- Set the sequence ownership
                        ALTER SEQUENCE family_members_id_seq OWNED BY family_members.id;
                        
                        -- Set the sequence to start from the max existing id + 1
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

# ==================== SYSTEM PROMPT ====================

SYSTEM_PROMPT = """You are Tree of Life AI, an integrative health intelligence assistant."""

# ==================== STARTUP EVENT ====================

@app.on_event("startup")
async def startup_event():
    print("🌳 Starting Tree of Life AI...")
    
    # FIX: Ensure family_members.id is INTEGER before creating new tables
    print("🔧 Checking family_members.id data type...")
    try:
        with engine.connect() as conn:
            # Check current data type
            result = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'family_members' 
                AND column_name = 'id'
            """))
            row = result.fetchone()
            
            if row and row[0] != 'integer':
                print(f"  ⚠️ family_members.id is {row[0]}, converting to INTEGER...")
                
                # Drop foreign key constraints if any exist
                conn.execute(text("ALTER TABLE IF EXISTS client_protocols DROP CONSTRAINT IF EXISTS client_protocols_client_id_fkey CASCADE"))
                conn.commit()
                
                # Convert id column to INTEGER
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
    
    # FIX conversations table
    print("🔧 Fixing conversations table...")
    try:
        with engine.connect() as conn:
            # Drop and recreate conversations table
            conn.execute(text("DROP TABLE IF EXISTS messages CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        print("✅ Conversations table recreated")
    except Exception as e:
        print(f"⚠️ Conversations fix: {e}")
    
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
        
        # Delete all user data
        db.query(Message).filter(Message.conversation_id.in_(
            db.query(Conversation.id).filter(Conversation.user_id == user_id)
        )).delete(synchronize_session=False)
        
        db.query(Conversation).filter(Conversation.user_id == user_id).delete()
        db.query(FamilyMember).filter(FamilyMember.user_id == user_id).delete()
        db.query(HealthProfile).filter(HealthProfile.user_id == user_id).delete()
        db.query(HealthMetric).filter(HealthMetric.user_id == user_id).delete()
        
        # Delete lab results if table exists
        try:
            db.execute(text("DELETE FROM lab_results WHERE user_id = :user_id"), {'user_id': str(user_id)})
        except:
            pass
        
        # Delete user
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
    
    with get_db_context() as db:
        # Create conversation
        conversation = Conversation(user_id=user_id, title=data.initial_message[:50])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        # Add user message
        user_message = Message(
            conversation_id=conversation.id,
            role='user',
            content=data.initial_message
        )
        db.add(user_message)
        db.commit()
        
        # Get AI response
        messages = [{"role": "user", "content": data.initial_message}]
        
        # Add image if present
        if data.image:
            messages[0] = {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": data.image['type'], "data": data.image['data']}},
                    {"type": "text", "text": data.initial_message}
                ]
            }
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=messages
        )
        
        ai_content = response.content[0].text
        
        # Add AI message
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
    
    with get_db_context() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Add user message
        user_message = Message(
            conversation_id=conversation_id,
            role='user',
            content=data.message
        )
        db.add(user_message)
        db.commit()
        
        # Get conversation history
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()
        
        # Build message array for Claude
        claude_messages = []
        for msg in messages:
            claude_messages.append({"role": msg.role, "content": msg.content})
        
        # Add image if present in current message
        if data.image:
            claude_messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": data.image['type'], "data": data.image['data']}},
                    {"type": "text", "text": data.message}
                ]
            }
        
        # Get AI response
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=claude_messages
        )
        
        ai_content = response.content[0].text
        
        # Add AI message
        ai_message = Message(
            conversation_id=conversation_id,
            role='assistant',
            content=ai_content
        )
        db.add(ai_message)
        db.commit()
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "message": {
                "role": "assistant",
                "content": ai_content,
                "timestamp": ai_message.timestamp.isoformat()
            }
        }

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
        
        # Delete messages
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        
        # Delete conversation
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
    recorded_at: str  # ISO format datetime

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
    
    recent = metrics[-5:]  # Last 5 entries
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
async def ai_health_analysis(
    health_data: dict,
    request: Request
):
    """Generate comprehensive AI health analysis with clinical nutrition and supplement recommendations"""
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
8. **Clinical Nutrition**: Specific nutritional therapy recommendations based on deficiencies, conditions, and goals
9. **Herbal Medicine**: Evidence-based herbal remedies appropriate for their conditions (with safety considerations)
10. **Supplement Recommendations**: Specific supplements with dosages, timing, and rationale (considering interactions with medications)
11. **Ayurvedic Perspective**: Recommendations based on dosha (if applicable)
12. **TCM Perspective**: Recommendations based on pattern (if applicable)
13. **Action Items**: Specific, actionable steps to improve health

IMPORTANT for Clinical Nutrition & Supplements:
- Consider nutrient deficiencies based on lab results
- Account for medication-nutrient interactions
- Recommend specific dosages and optimal timing
- Prioritize food sources over supplements when possible
- Note any contraindications with current medications
- Include quality/form recommendations (e.g., methylated B vitamins, chelated minerals)
- Suggest appropriate monitoring (e.g., recheck vitamin D levels in 3 months)

Use markdown formatting. Be compassionate, clear, and actionable. Highlight any concerning findings 
that warrant medical attention. Emphasize the integrative approach combining ancient wisdom with modern science.

Remember: This is for informational purposes only and does not replace professional medical advice."""

        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        analysis_text = message.content[0].text
        sections = _parse_analysis_sections(analysis_text)

        return JSONResponse(content=sections)

    except Exception as e:
        print(f"❌ AI analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="AI analysis failed")


@app.post("/api/health/explain-value")
async def explain_lab_value(
    request_data: dict,
    request: Request
):
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

Use simple language that a non-medical person can understand. Be reassuring but honest about any concerns."""

        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

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

# ==================== LAB RESULTS ENDPOINTS ====================

# ==================== FIXED LAB RESULTS UPLOAD ENDPOINT ====================
# Replace your existing @app.post("/api/lab-results/upload") function with this

@app.post("/api/lab-results/upload")
async def upload_lab_result(
    request: Request,
    file: UploadFile = File(...),
    provider: str = Form(...),
    test_date: str = Form(...)
):
    """Upload and extract lab results from image or PDF"""
    user_id = get_current_user_id(request)
    
    # ==================== FILE VALIDATION ====================
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type '{file.content_type}'. Please upload JPG, PNG, or PDF only."
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )
    
    print(f"📄 Processing lab results upload: {file.filename} ({len(file_content)} bytes)")
    
    # ==================== PREPARE FOR AI EXTRACTION ====================
    
    try:
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Determine media type
        media_type = file.content_type
        if file.filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif file.filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif file.filename.lower().endswith('.png'):
            media_type = "image/png"
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Build content block based on file type
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
        
        # ==================== IMPROVED EXTRACTION PROMPT ====================
        
        extraction_prompt = """You are a medical lab results extraction expert. Extract ALL lab test values from this document.

CRITICAL INSTRUCTIONS:
1. Extract EVERY test result you can find
2. For EACH test, provide ALL four fields: name, value, unit, reference_range
3. Return ONLY valid JSON - no markdown, no explanations

REQUIRED JSON FORMAT:
{
  "test_type": "Name of the lab panel (e.g., 'Basic Metabolic Panel', 'Lipid Panel', 'Complete Blood Count')",
  "results": [
    {
      "name": "TEST NAME (e.g., 'SODIUM', 'Glucose', 'Hemoglobin')",
      "value": "NUMERIC VALUE ONLY (e.g., '143', '4.5', '92')",
      "unit": "UNIT (e.g., 'mEq/L', 'mg/dL', 'g/dL', '%')",
      "reference_range": "RANGE (e.g., '135-145', '70-100', '<5.7', '>50')"
    }
  ]
}

EXTRACTION RULES:
- Test names are usually in CAPS or bold (SODIUM, POTASSIUM, GLUCOSE, etc.)
- Values are the numbers next to test names (143, 4.1, 5.7, etc.)
- Units come after values (mEq/L, mg/dL, g/dL, %, etc.)
- Reference ranges are labeled "Normal range:", "Reference:", "Range:", or appear as "135-145 mEq/L"
- If you see "Normal range: 135 - 145", extract as "135-145"
- If you see "<5.7" or ">50", include the < or > symbol
- Extract the actual test name from the document, not a description

IMPORTANT:
- Do NOT skip any tests
- Do NOT leave any field empty - if you can't find reference_range, put "N/A"
- Do NOT add explanations or comments
- Return ONLY the JSON object

Now extract all lab values from this document:"""

        # ==================== CALL CLAUDE API ====================
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            temperature=0,  # Use 0 for consistent extraction
            messages=[{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": extraction_prompt}
                ]
            }]
        )
        
        response_text = message.content[0].text
        print(f"🤖 Raw AI Response:\n{response_text}\n")
        
        # ==================== PARSE JSON RESPONSE ====================
        
        # Clean up response - remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"Attempted to parse: {response_text[:500]}...")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse extracted data. Please try uploading a clearer image."
            )
        
        # ==================== VALIDATE EXTRACTION ====================
        
        # Ensure proper structure
        if not isinstance(extracted_data, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid extraction format. Please try again."
            )
        
        if 'results' not in extracted_data:
            extracted_data['results'] = []
        
        if not isinstance(extracted_data['results'], list):
            extracted_data['results'] = []
        
        # Validate each result has required fields
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
        
        # ==================== ADD METADATA ====================
        
        extracted_data['provider'] = provider
        extracted_data['test_date'] = test_date
        extracted_data['file_url'] = f"uploaded/{file.filename}"
        
        # Set default test_type if not provided
        if 'test_type' not in extracted_data or not extracted_data['test_type']:
            extracted_data['test_type'] = 'Lab Results'
        
        print(f"✅ Successfully extracted {len(validated_results)} lab values")
        print(f"📊 Test type: {extracted_data.get('test_type')}")
        
        return extracted_data
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
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
        # Ensure file_url column exists (for existing tables)
        try:
            conn.execute(text("""
                ALTER TABLE lab_results 
                ADD COLUMN IF NOT EXISTS file_url TEXT
            """))
            conn.commit()
            print("✅ Ensured file_url column exists")
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
# ==================== PRO PROTOCOL MODELS ====================

class Protocol(Base):
    __tablename__ = "protocols"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    traditions = Column(String)  # "Ayurveda + TCM"
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
    herbs_supplements = Column(JSON)  # [{"name": "Ashwagandha", "dosage": "500mg 2x daily"}]
    lifestyle_changes = Column(JSON)  # ["Meditation 10min daily", "Sleep by 10pm"]
    created_at = Column(DateTime, default=datetime.utcnow)

class ClientProtocol(Base):
    __tablename__ = "client_protocols"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # practitioner
    client_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    protocol_id = Column(Integer, ForeignKey('protocols.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    current_week = Column(Integer, default=1)
    status = Column(String, default='active')  # active, paused, completed
    completion_percentage = Column(Integer, default=0)
    assigned_at = Column(DateTime, default=datetime.utcnow)

class ComplianceLog(Base):
    __tablename__ = "compliance_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_protocol_id = Column(Integer, ForeignKey('client_protocols.id'), nullable=False)
    week_number = Column(Integer, nullable=False)
    compliance_score = Column(Integer)  # 0-100
    notes = Column(Text)
    logged_at = Column(DateTime, default=datetime.utcnow)

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

# Protocols CRUD
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

# Protocol Phases
@app.get("/api/protocols/{protocol_id}/phases")
async def get_protocol_phases(request: Request, protocol_id: int):
    """Get all phases for a protocol"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Verify ownership
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
        # Verify ownership
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
        # Verify ownership
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

# Protocol Assignment
@app.post("/api/protocols/{protocol_id}/assign")
async def assign_protocol(request: Request, protocol_id: int, assignment: ProtocolAssign):
    """Assign a protocol to a client"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Verify protocol ownership
        protocol = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        # Verify client ownership
        client = db.query(FamilyMember).filter(
            FamilyMember.id == assignment.client_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Create assignment
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

# Compliance Tracking
@app.post("/api/compliance")
async def log_compliance(request: Request, compliance: ComplianceCreate):
    """Log client compliance"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Verify ownership
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.id == compliance.client_protocol_id,
            ClientProtocol.user_id == user_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        # Create compliance log
        log = ComplianceLog(
            client_protocol_id=compliance.client_protocol_id,
            week_number=compliance.week_number,
            compliance_score=compliance.compliance_score,
            notes=compliance.notes
        )
        db.add(log)
        
        # Update assignment progress
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
        # Verify ownership
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

# Analytics
@app.get("/api/analytics/dashboard")
async def get_analytics(request: Request):
    """Get analytics data for dashboard"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Total clients
        total_clients = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).count()
        
        # Active protocols
        active_assignments = db.query(ClientProtocol).filter(
            ClientProtocol.user_id == user_id,
            ClientProtocol.status == 'active'
        ).count()
        
        # Average completion rate
        all_assignments = db.query(ClientProtocol).filter(
            ClientProtocol.user_id == user_id
        ).all()
        
        avg_completion = sum(a.completion_percentage for a in all_assignments) / len(all_assignments) if all_assignments else 0
        
        # Compliance data
        recent_logs = db.query(ComplianceLog).join(ClientProtocol).filter(
            ClientProtocol.user_id == user_id
        ).order_by(ComplianceLog.logged_at.desc()).limit(10).all()
        
        avg_compliance = sum(log.compliance_score for log in recent_logs) / len(recent_logs) if recent_logs else 0
        
        return {
            "total_clients": total_clients,
            "active_protocols": active_assignments,
            "avg_completion": round(avg_completion, 1),
            "avg_compliance": round(avg_compliance, 1),
            "client_retention": 92,  # Placeholder
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
