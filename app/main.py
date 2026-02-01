import secrets
from datetime import datetime, timedelta
import resend
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Boolean, Text, JSON, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import os
import jwt
import bcrypt
import anthropic
import stripe
import base64
import json
import asyncio
from app.api import client_messages
from typing import Optional, List, Dict
from app.enhanced_system_prompt import SYSTEM_PROMPT_WITH_WESTERN_MED
from app.skill_loader import get_specialized_knowledge
resend.api_key = os.environ.get('RESEND_API_KEY')

# Near top of main.py, after imports
MESSAGE_LIMITS = {
    'free': 10,      # 10 messages/month
    'basic': 50,     # 50 messages/month  
    'premium': 200,  # 200 messages/month
    'pro': None       # None = unlimited
}
# Add this helper function
def check_message_limit(user_id, tier):
    """Check if user has exceeded monthly message limit"""
    limit = MESSAGE_LIMITS.get(tier, MESSAGE_LIMITS['free'])
    
    # Pro tier is unlimited
    if limit is None:
        return
    
    with get_db_context() as db:
        from datetime import datetime
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        message_count = db.query(Message).join(Conversation).filter(
            Conversation.user_id == user_id,
            Message.timestamp >= current_month_start,
            Message.role == 'user'
        ).count()
        
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
ALGORITHM = "HS256"
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_PROJECT_ID = os.getenv('ANTHROPIC_PROJECT_ID')  # ← NEW: Add this to your Render environment variables
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = STRIPE_SECRET_KEY

# ==================== ANTHROPIC SETUP ====================
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ==================== STRIPE PRICE IDS ====================
STRIPE_PRICES = {
    'basic_monthly': os.getenv('STRIPE_BASIC_PRICE_ID'),
    'basic_annual': os.getenv('BASIC_ANNUAL_PRICE_ID'),
    'premium_monthly': os.getenv('STRIPE_PREMIUM_PRICE_ID'),
    'premium_annual': os.getenv('PREMIUM_ANNUAL_PRICE_ID'),
    'pro_monthly': os.getenv('STRIPE_PRO_PRICE_ID'),
    'pro_annual': os.getenv('PRO_ANNUAL_PRICE_ID'),
}

# ==================== DATABASE SETUP ====================

engine = create_engine(DATABASE_URL)
# ==================== AUTO MIGRATION ====================
def run_migrations():
    statements = [
        "CREATE TABLE IF NOT EXISTS weekly_checkins (id SERIAL PRIMARY KEY, client_protocol_id INTEGER NOT NULL REFERENCES client_protocols(id) ON DELETE CASCADE, week_number INTEGER NOT NULL, primary_symptom_rating INTEGER NOT NULL CHECK (primary_symptom_rating BETWEEN 1 AND 10), energy_level INTEGER NOT NULL CHECK (energy_level BETWEEN 1 AND 10), sleep_quality INTEGER NOT NULL CHECK (sleep_quality BETWEEN 1 AND 10), notes TEXT, what_helped TEXT, what_struggled TEXT, submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS protocol_outcomes (id SERIAL PRIMARY KEY, client_protocol_id INTEGER NOT NULL REFERENCES client_protocols(id) ON DELETE CASCADE, protocol_id INTEGER NOT NULL REFERENCES protocols(id), overall_effectiveness INTEGER CHECK (overall_effectiveness BETWEEN 1 AND 5), symptoms_improved BOOLEAN, would_recommend BOOLEAN, what_improved_most TEXT, what_was_hardest TEXT, suggestions TEXT, practitioner_effectiveness INTEGER CHECK (practitioner_effectiveness BETWEEN 1 AND 5), completed_by VARCHAR(50) DEFAULT 'client', submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(client_protocol_id))",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_checkins_unique ON weekly_checkins(client_protocol_id, week_number, DATE(submitted_at))",
        "CREATE INDEX IF NOT EXISTS idx_weekly_checkins_protocol ON weekly_checkins(client_protocol_id)",
        "CREATE INDEX IF NOT EXISTS idx_weekly_checkins_week ON weekly_checkins(week_number)",
        "CREATE INDEX IF NOT EXISTS idx_weekly_checkins_date ON weekly_checkins(submitted_at)",
        "CREATE INDEX IF NOT EXISTS idx_protocol_outcomes_protocol ON protocol_outcomes(protocol_id)",
        "CREATE INDEX IF NOT EXISTS idx_protocol_outcomes_effectiveness ON protocol_outcomes(overall_effectiveness)"
    ]
    try:
        with engine.connect() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
        print("✅ Migrations complete")
    except Exception as e:
        print(f"Migration error: {e}")

run_migrations()
# ==================== END MIGRATION ====================
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
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
    
    # Protocol content fields
    supplements = Column(JSON)
    exercises = Column(JSON)
    lifestyle_changes = Column(JSON)
    nutrition = Column(JSON)
    sleep = Column(JSON)
    stress_management = Column(Text)
    weekly_notes = Column(JSON)
    
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
# ==================== CLIENT PORTAL MODELS ====================


class ClientMessage(Base):
    __tablename__ = "client_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    family_member_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    practitioner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    message_text = Column(Text, nullable=False)
    image_base64 = Column(Text)
    is_read = Column(Boolean, default=False)
    replied_at = Column(DateTime)
    reply_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
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
            
            # ==================== CLIENT PORTAL TABLES ====================
            
            print("🔗 Checking client portal tables...")
            try:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'client_view_tokens'
                    )
                """))
                table_exists = result.fetchone()[0]
                
                if not table_exists:
                    print("  📝 Creating client_view_tokens table...")
                    conn.execute(text("""
                        CREATE TABLE client_view_tokens (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                            practitioner_id UUID REFERENCES users(id) ON DELETE CASCADE,
                            token VARCHAR(255) UNIQUE NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_accessed TIMESTAMP,
                            is_active BOOLEAN DEFAULT true
                        )
                    """))
                    conn.commit()
                    print("  ✅ client_view_tokens table created")
                else:
                    print("  ✅ client_view_tokens table exists (preserved)")
                    
            except Exception as e:
                print(f"  ⚠️ client_view_tokens: {e}")
            
            try:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'client_messages'
                    )
                """))
                table_exists = result.fetchone()[0]
                
                if not table_exists:
                    print("  📝 Creating client_messages table...")
                    conn.execute(text("""
                        CREATE TABLE client_messages (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                            practitioner_id UUID REFERENCES users(id) ON DELETE CASCADE,
                            message_text TEXT NOT NULL,
                            image_base64 TEXT,
                            is_read BOOLEAN DEFAULT false,
                            replied_at TIMESTAMP,
                            reply_text TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.commit()
                    print("  ✅ client_messages table created")
                else:
                    print("  ✅ client_messages table exists (preserved)")
                    
            except Exception as e:
                print(f"  ⚠️ client_messages: {e}")
            
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_client_messages_practitioner 
                    ON client_messages(practitioner_id, is_read)
                """))
                conn.commit()
                print("  ✅ client_messages index created")
            except Exception as e:
                print(f"  ⚠️ index creation: {e}")
            # ==================== TWO-WAY MESSAGING MIGRATION ====================
            
            print("💬 Adding two-way messaging support...")
            try:
                # Add sender_type column for tracking message sender
                conn.execute(text("""
                    ALTER TABLE client_messages 
                    ADD COLUMN IF NOT EXISTS sender_type VARCHAR(20) DEFAULT 'client'
                """))
                conn.commit()
                print("  ✅ sender_type column added")
                
                # Update existing messages to be from 'client'
                conn.execute(text("""
                    UPDATE client_messages 
                    SET sender_type = 'client' 
                    WHERE sender_type IS NULL
                """))
                conn.commit()
                print("  ✅ Existing messages marked as 'client'")
                
                # Make sender_type NOT NULL
                try:
                    conn.execute(text("""
                        ALTER TABLE client_messages 
                        ALTER COLUMN sender_type SET NOT NULL
                    """))
                    conn.commit()
                    print("  ✅ sender_type set to NOT NULL")
                except Exception as e:
                    print(f"  ℹ️ sender_type constraint: {e}")
                
                # Add index for faster thread retrieval
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_client_messages_thread 
                    ON client_messages(family_member_id, created_at DESC)
                """))
                conn.commit()
                print("  ✅ Thread index created")
                
            except Exception as e:
                print(f"  ⚠️ Two-way messaging migration: {e}")
            
            print("✅ Two-way messaging ready!")
            print("✅ Client portal tables ready!")
            
            # ==================== PROTOCOL CONTENT FIELDS ====================
            
            print("🌿 Checking protocol content fields...")
            protocol_migrations = [
                "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS supplements JSONB",
                "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS exercises JSONB",
                "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS lifestyle_changes JSONB",
                "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS nutrition JSONB",
                "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS sleep JSONB",
                "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS stress_management TEXT",
                "ALTER TABLE protocols ADD COLUMN IF NOT EXISTS weekly_notes JSONB"
            ]
            
            for query in protocol_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"  ⚠️  Protocol field: {e}")
            
            print("✅ Protocol content fields checked!")
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        raise
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        raise
    
    print("✅ Database migration completed!")

# ==================== FASTAPI APP ====================
app = FastAPI(title="Tree of Life AI API")
import os
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    print("✅ Static files mounted from app/static/")
else:
    print("⚠️  /app/static/ directory not found - PWA features disabled")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register client inbox routes
app.include_router(client_messages.router, prefix="/api", tags=["client-messages"])
from app.api.client_portal import router as client_portal_router
app.include_router(client_portal_router, prefix="/api", tags=["client-portal"])
from app.api.client_portal import router as client_portal_router
app.include_router(client_portal_router, prefix="/api", tags=["client-portal"])
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
# Auth functions moved to app/auth.py to avoid circular imports
from app.auth import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
    get_current_user_id
)

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
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        hashed_password = user.hashed_password
        user_id = user.id
        user_email = user.email
        user_name = user.full_name
    
    try:
        password_valid = verify_password(request.password, hashed_password)
    except (ValueError, Exception) as e:
        print(f"❌ Password verification failed for {request.email}: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not password_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user_id)
    return {"token": token, "user": {"email": user_email, "name": user_name}}
        
@app.post("/api/auth/request-password-reset")
async def request_password_reset(data: dict):
    """Request password reset - sends email with reset link"""
    email = data.get('email', '').strip().lower()
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    with get_db_context() as db:
        user = db.execute(text(
            "SELECT id, email, full_name FROM users WHERE email = :email"
        ), {'email': email}).fetchone()
        
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            db.execute(text(
                "UPDATE password_reset_tokens SET used = true WHERE user_id = :user_id AND used = false"
            ), {'user_id': str(user[0])})
            
            db.execute(text(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (:user_id, :token, :expires_at)"
            ), {
                'user_id': str(user[0]),
                'token': token,
                'expires_at': expires_at
            })
            db.commit()
            
            reset_link = f"https://www.treeoflifeai.com/reset-password.html?token={token}"
            
            # Send email
            try:
                resend.Emails.send({
                    "from": "noreply@treeoflifeai.com",
                    "to": email, 
                    "subject": "Reset Your Tree of Life AI Password",
                    "html": f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #D4A574;">Reset Your Password</h2>
                        <p>Click the link below to reset your password:</p>
                        <a href="{reset_link}" style="display: inline-block; padding: 12px 24px; background: #B8860B; color: white; text-decoration: none; border-radius: 8px; margin: 20px 0;">Reset Password</a>
                        <p style="color: #666; font-size: 14px;">This link expires in 1 hour.</p>
                        <p style="color: #999; font-size: 12px;">If you didn't request this, ignore this email.</p>
                    </div>
                    """
                })
                print(f"✅ Password reset email sent to {email}")
            except Exception as e:
                print(f"❌ Email send failed: {e}")
    
    return {"success": True, "message": "If that email exists, you'll receive a password reset link shortly."}


@app.post("/api/auth/reset-password")
async def reset_password(data: dict):
    """Reset password using token"""
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new password required")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    with get_db_context() as db:
        reset_token = db.execute(text(
            "SELECT user_id, expires_at, used FROM password_reset_tokens WHERE token = :token"
        ), {'token': token}).fetchone()
        
        if not reset_token:
            raise HTTPException(status_code=400, detail="Invalid or expired reset link")
        
        if reset_token[2]:
            raise HTTPException(status_code=400, detail="This reset link has already been used")
        
        if datetime.utcnow() > reset_token[1]:
            raise HTTPException(status_code=400, detail="This reset link has expired")
        
        user_id = reset_token[0]
        hashed_password = hash_password(new_password)
        
        db.execute(text(
            "UPDATE users SET hashed_password = :hashed_password WHERE id = :user_id"
        ), {'hashed_password': hashed_password, 'user_id': str(user_id)})
        
        db.execute(text(
            "UPDATE password_reset_tokens SET used = true WHERE token = :token"
        ), {'token': token})
        
        db.commit()
    
    return {"success": True, "message": "Password successfully reset. You can now log in with your new password."}
    
# Rename the endpoint
@app.get("/api/auth/me")
async def me_endpoint(request: Request):
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

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jwt.exceptions import InvalidTokenError as JWTError

security = HTTPBearer(auto_error=False)

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Optional JWT auth - returns user if logged in, None if guest"""
    if not credentials:
        return None
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return {"sub": user_id}
    except JWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Required JWT auth - raises error if not logged in"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"sub": user_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
@app.delete("/api/auth/account")
async def delete_account(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account and ALL associated data.
    Order matters due to foreign key constraints.
    """
    try:
        user_id = current_user['sub']
        
        # ✅ STEP 1: Cancel Stripe subscription first
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.stripe_customer_id:
                try:
                    subscriptions = stripe.Subscription.list(
                        customer=user.stripe_customer_id,
                        status='active'
                    )
                    for subscription in subscriptions.data:
                        stripe.Subscription.delete(subscription.id)
                except Exception as stripe_error:
                    print(f"Stripe cancellation error: {stripe_error}")
                    # Continue with deletion even if Stripe fails
        except Exception as e:
            print(f"Error canceling subscription: {e}")        
      
       # REPLACE your entire STEP 2 in delete_account with this:

        # ✅ STEP 2: Delete in correct order based on actual schema
        
        # Level 1: Delete grandchildren (compliance_logs -> client_protocols -> family_members -> users)
        db.execute(
            text("""
                DELETE FROM compliance_logs 
                WHERE client_protocol_id IN (
                    SELECT cp.id FROM client_protocols cp
                    JOIN family_members fm ON cp.client_id = fm.id
                    WHERE fm.user_id = :user_id
                )
            """),
            {"user_id": user_id}
        )
        
        # Level 2: Delete children of family_members
        db.execute(
            text("""
                DELETE FROM client_protocols 
                WHERE client_id IN (SELECT id FROM family_members WHERE user_id = :user_id)
            """),
            {"user_id": user_id}
        )
        
        db.execute(
            text("""
                DELETE FROM ai_analyses 
                WHERE client_id IN (SELECT id FROM family_members WHERE user_id = :user_id)
            """),
            {"user_id": user_id}
        )
        
        db.execute(
            text("""
                DELETE FROM client_messages 
                WHERE family_member_id IN (SELECT id FROM family_members WHERE user_id = :user_id)
            """),
            {"user_id": user_id}
        )
        
        db.execute(
            text("""
                DELETE FROM client_view_tokens 
                WHERE family_member_id IN (SELECT id FROM family_members WHERE user_id = :user_id)
            """),
            {"user_id": user_id}
        )
        
        db.execute(
            text("""
                DELETE FROM health_profiles 
                WHERE family_member_id IN (SELECT id FROM family_members WHERE user_id = :user_id)
            """),
            {"user_id": user_id}
        )
        
        # Level 3: Delete children of custom_protocols
        db.execute(
            text("""
                DELETE FROM client_records 
                WHERE active_protocol_id IN (SELECT id FROM custom_protocols WHERE user_id = :user_id)
            """),
            {"user_id": user_id}
        )
        
        # Level 4: Delete direct children of users
        db.execute(
            text("DELETE FROM client_messages WHERE practitioner_id = :user_id"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM client_records WHERE practitioner_id = :user_id"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM client_view_tokens WHERE practitioner_id = :user_id"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM custom_protocols WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM family_members WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM health_profiles WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM lab_results WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM health_metrics WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        # Level 5: Delete conversations and messages
        db.execute(
            text("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = :user_id)"),
            {"user_id": user_id}
        )
        
        db.execute(
            text("DELETE FROM conversations WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        # ✅ STEP 3: Finally delete the user account
        db.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        
        # ✅ STEP 4: Commit all deletions
        db.commit()
        
        return {
            "success": True,
            "message": "Account and all data permanently deleted"
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error deleting account: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting account data: {str(e)}"
        )
    finally:
        db.close()

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
        
        # Delete related records first (in correct order)
        
        # 1. Delete compliance logs for this client's protocols
        db.execute(text("""
            DELETE FROM compliance_logs
            WHERE client_protocol_id IN (
                SELECT id FROM client_protocols WHERE client_id = :member_id
            )
        """), {'member_id': member_id})
        
        # 2. Delete client protocol assignments
        db.execute(text("""
            DELETE FROM client_protocols WHERE client_id = :member_id
        """), {'member_id': member_id})
        
        # 3. Delete client view tokens (has CASCADE but being explicit)
        db.execute(text("""
            DELETE FROM client_view_tokens WHERE family_member_id = :member_id
        """), {'member_id': member_id})
        
        # 4. Delete client messages (has CASCADE but being explicit)
        db.execute(text("""
            DELETE FROM client_messages WHERE family_member_id = :member_id
        """), {'member_id': member_id})
        
        # 5. Finally delete the family member
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
async def create_checkout(request: Request, current_user: dict = Depends(get_current_user_optional)):
    # Parse JSON body first
    data = await request.json()
    tier = data.get('tier')
    billing = data.get('billing', 'monthly')
    
    price_key = f"{tier}_{billing}"
    
    if price_key not in STRIPE_PRICES:
        raise HTTPException(status_code=400, detail=f"Invalid tier/billing combination: {price_key}")
    
    price_id = STRIPE_PRICES[price_key]
    if not price_id:
        raise HTTPException(status_code=500, detail=f"Stripe price not configured for {price_key}")
    
    # Handle logged-in users
    customer_id = None
    user_id_str = None
    
    if current_user:
        with get_db_context() as db:
            user = db.query(User).filter(User.id == current_user['sub']).first()
            if user:
                if not user.stripe_customer_id:
                    customer = stripe.Customer.create(
                        email=user.email,
                        metadata={'user_id': str(user.id)}
                    )
                    user.stripe_customer_id = customer.id
                    db.commit()
                customer_id = user.stripe_customer_id
                user_id_str = str(user.id)
    
    # Cancel any existing active subscriptions before creating new one
    if customer_id:
        try:
            existing_subs = stripe.Subscription.list(
                customer=customer_id,
                status='active',
                limit=10
            )
            for sub in existing_subs.data:
                stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
        except Exception as e:
            print(f"⚠️ Error canceling existing subscriptions: {e}")
    
    # Create checkout session
    try:
        session_params = {
            'payment_method_types': ['card'],
            'line_items': [{'price': price_id, 'quantity': 1}],
            'mode': 'subscription',
            'success_url': 'https://treeoflifeai.com/subscriptions.html?success=true',
            'cancel_url': 'https://treeoflifeai.com/index.html'
        }
        
        if customer_id:
            session_params['customer'] = customer_id
            session_params['client_reference_id'] = user_id_str
            session_params['metadata'] = {'user_id': user_id_str, 'tier': tier}
        
        checkout_session = stripe.checkout.Session.create(**session_params)
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
    elif event['type'] == 'customer.subscription.deleted':
        session = event['data']['object']
        customer_id = session.get('customer')
        
        if customer_id:
            with get_db_context() as db:
                user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
                if user:
                    user.subscription_tier = 'free'
                    user.family_member_limit = 0
                    user.stripe_subscription_id = None
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
# ==================== AI ANALYSIS ENDPOINTS ====================

@app.post("/api/health/ai-analysis/save")
async def save_ai_analysis(request: Request):
    """Save AI health analysis for a client"""
    try:
        user_id = get_current_user_id(request)
        data = await request.json()
        client_id = data.get('client_id')
        analysis_data = data.get('analysis_data')
        
        if not client_id or not analysis_data:
            raise HTTPException(status_code=400, detail="Missing client_id or analysis_data")
        
        with get_db_context() as db:
            # Verify client belongs to this practitioner
            member = db.query(FamilyMember).filter(
                FamilyMember.id == client_id,
                FamilyMember.user_id == user_id
            ).first()
            
            if not member:
                raise HTTPException(status_code=404, detail="Client not found")
            
            # Save analysis to PostgreSQL
            with engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO ai_analyses (user_id, client_id, analysis_data, created_at)
                    VALUES (:user_id, :client_id, :analysis_data, :created_at)
                    RETURNING id
                """), {
                    'user_id': str(user_id),
                    'client_id': client_id,
                    'analysis_data': json.dumps(analysis_data),
                    'created_at': datetime.now()
                })
                
                analysis_id = result.fetchone()[0]
                conn.commit()
        
        return {
            'success': True,
            'analysis_id': analysis_id,
            'message': 'Analysis saved successfully'
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error saving AI analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health/ai-analysis/history/{client_id}")
async def get_analysis_history(request: Request, client_id: int):
    """Get all AI analyses for a specific client"""
    try:
        user_id = get_current_user_id(request)
        
        with get_db_context() as db:
            # Verify client belongs to this practitioner
            member = db.query(FamilyMember).filter(
                FamilyMember.id == client_id,
                FamilyMember.user_id == user_id
            ).first()
            
            if not member:
                raise HTTPException(status_code=404, detail="Client not found")
        
        # Get all analyses for this client
        with engine.connect() as conn:
            results = conn.execute(text("""
                SELECT id, created_at
                FROM ai_analyses
                WHERE client_id = :client_id AND user_id = :user_id
                ORDER BY created_at DESC
            """), {
                'client_id': client_id,
                'user_id': str(user_id)
            })
            
            analyses = []
            for row in results:
                analyses.append({
                    'id': row[0],
                    'created_at': row[1].isoformat()
                })
        
        return {
            'analyses': analyses,
            'count': len(analyses)
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error fetching analysis history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health/ai-analysis/{analysis_id}")
async def get_analysis(request: Request, analysis_id: int):
    """Get a specific AI analysis by ID"""
    try:
        user_id = get_current_user_id(request)
        
        # Get analysis
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, user_id, client_id, analysis_data, created_at, updated_at
                FROM ai_analyses
                WHERE id = :analysis_id AND user_id = :user_id
            """), {
                'analysis_id': analysis_id,
                'user_id': str(user_id)
            })
            
            row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {
            'id': row[0],
            'user_id': str(row[1]),
            'client_id': row[2],
            'analysis_data': row[3],
            'created_at': row[4].isoformat(),
            'updated_at': row[5].isoformat() if row[5] else None
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error fetching analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/health/ai-analysis/{analysis_id}")
async def delete_analysis(request: Request, analysis_id: int):
    """Delete a specific AI analysis"""
    try:
        user_id = get_current_user_id(request)
        
        # Delete analysis
        with engine.connect() as conn:
            result = conn.execute(text("""
                DELETE FROM ai_analyses
                WHERE id = :analysis_id AND user_id = :user_id
            """), {
                'analysis_id': analysis_id,
                'user_id': str(user_id)
            })
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Analysis not found")
            
            conn.commit()
        
        return {
            'success': True,
            'message': 'Analysis deleted successfully'
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error deleting analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
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
    """Get all protocols for current user with full content"""
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
            "supplements": p.supplements,
            "exercises": p.exercises,
            "lifestyle_changes": p.lifestyle_changes,
            "nutrition": p.nutrition,
            "sleep": p.sleep,
            "stress_management": p.stress_management,
            "weekly_notes": p.weekly_notes,
            "created_at": p.created_at.isoformat()
        } for p in protocols]}
        
@app.get("/api/protocols/{protocol_id}")
async def get_protocol(request: Request, protocol_id: int):
    """Get a single protocol by ID"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        protocol = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not protocol:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        return {
            "protocol": {
                "id": protocol.id,
                "name": protocol.name,
                "traditions": protocol.traditions,
                "description": protocol.description,
                "duration_weeks": protocol.duration_weeks,
                "supplements": protocol.supplements,
                "exercises": protocol.exercises,
                "lifestyle_changes": protocol.lifestyle_changes,
                "nutrition": protocol.nutrition,
                "sleep": protocol.sleep,
                "stress_management": protocol.stress_management,
                "weekly_notes": protocol.weekly_notes,
                "created_at": protocol.created_at.isoformat()
            }
        }

@app.post("/api/protocols")
async def create_protocol(request: Request):
    """Create a new protocol with all content fields"""
    user_id = get_current_user_id(request)
    data = await request.json()
    
    with get_db_context() as db:
        new_protocol = Protocol(
            user_id=user_id,
            name=data.get('name', 'Untitled Protocol'),
            traditions=data.get('traditions'),
            description=data.get('description'),
            duration_weeks=data.get('duration_weeks', 4),
            supplements=data.get('supplements'),
            exercises=data.get('exercises'),
            lifestyle_changes=data.get('lifestyle_changes'),
            nutrition=data.get('nutrition'),
            sleep=data.get('sleep'),
            stress_management=data.get('stress_management'),
            weekly_notes=data.get('weekly_notes')
        )
        db.add(new_protocol)
        db.commit()
        db.refresh(new_protocol)
        
        return {"id": new_protocol.id, "name": new_protocol.name}
@app.put("/api/protocols/{protocol_id}")
async def update_protocol(request: Request, protocol_id: int):
    """Update a protocol with all content fields"""
    user_id = get_current_user_id(request)
    data = await request.json()
    
    with get_db_context() as db:
        existing = db.query(Protocol).filter(
            Protocol.id == protocol_id,
            Protocol.user_id == user_id
        ).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Protocol not found")
        
        # Update basic fields
        if 'name' in data:
            existing.name = data['name']
        if 'traditions' in data:
            existing.traditions = data['traditions']
        if 'description' in data:
            existing.description = data['description']
        if 'duration_weeks' in data:
            existing.duration_weeks = data['duration_weeks']
        
        # Update protocol content fields
        if 'supplements' in data:
            existing.supplements = data['supplements']
        if 'exercises' in data:
            existing.exercises = data['exercises']
        if 'lifestyle_changes' in data:
            existing.lifestyle_changes = data['lifestyle_changes']
        if 'nutrition' in data:
            existing.nutrition = data['nutrition']
        if 'sleep' in data:
            existing.sleep = data['sleep']
        if 'stress_management' in data:
            existing.stress_management = data['stress_management']
        if 'weekly_notes' in data:
            existing.weekly_notes = data['weekly_notes']
        
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
@app.delete("/api/client-protocols/remove/{client_id}")
async def remove_client_protocol(client_id: int, request: Request):
    """Remove active protocol from a client"""
    user_id = get_current_user_id(request)
    
    try:
        with get_db_context() as db:
            # Find active protocol assignment for this client
            assignment = db.query(ClientProtocol).filter(
                ClientProtocol.client_id == client_id,
                ClientProtocol.status == 'active'
            ).first()
            
            if not assignment:
                raise HTTPException(status_code=404, detail="No active protocol found")
            
            # Verify this client belongs to the current user
            client = db.query(FamilyMember).filter(
                FamilyMember.id == client_id,
                FamilyMember.user_id == user_id
            ).first()
            
            if not client:
                raise HTTPException(status_code=403, detail="Not your client")
            
            # Mark as completed/removed instead of deleting
            assignment.status = 'completed'
            db.commit()
            
            return {
                "success": True,
                "message": "Protocol removed successfully"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error removing protocol: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
        
@app.post("/api/client-protocols/{assignment_id}/advance-week")
async def advance_client_week(assignment_id: int, request: Request):
    """Practitioner advances client to next week"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Get assignment and verify ownership
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.id == assignment_id,
            ClientProtocol.user_id == user_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        # Get protocol to check total weeks
        protocol = db.query(Protocol).filter(Protocol.id == assignment.protocol_id).first()
        
        if assignment.current_week >= protocol.duration_weeks:
            raise HTTPException(status_code=400, detail="Already at final week")
        
        # Advance to next week
        assignment.current_week += 1
        
        # Update completion percentage
        assignment.completion_percentage = int((assignment.current_week / protocol.duration_weeks) * 100)
        
        db.commit()
        
        return {
            "success": True,
            "new_week": assignment.current_week,
            "completion_percentage": assignment.completion_percentage,
            "message": f"Advanced to Week {assignment.current_week}"
        }

@app.post("/api/client-protocols/{assignment_id}/reset-week")
async def reset_client_week(assignment_id: int, request: Request):
    """Reset client back to Week 1"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.id == assignment_id,
            ClientProtocol.user_id == user_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        assignment.current_week = 1
        assignment.completion_percentage = 0
        
        db.commit()
        
        return {
            "success": True,
            "message": "Reset to Week 1"
        } 
@app.post("/api/compliance")
async def log_compliance(request: Request, compliance: ComplianceCreate):
    """Log client compliance - UNIFIED system with submitted_by tracking"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.id == compliance.client_protocol_id,
            ClientProtocol.user_id == user_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        # ✅ UNIFIED: Use SQL to include submitted_by column
        db.execute(text("""
            INSERT INTO compliance_logs 
            (client_protocol_id, week_number, compliance_score, notes, submitted_by, logged_at)
            VALUES (:protocol_id, :week, :score, :notes, 'practitioner', CURRENT_TIMESTAMP)
        """), {
            'protocol_id': compliance.client_protocol_id,
            'week': compliance.week_number,
            'score': compliance.compliance_score,
            'notes': compliance.notes
        })        
        
        # Update protocol progress
        protocol = db.query(Protocol).filter(Protocol.id == assignment.protocol_id).first()
        assignment.current_week = compliance.week_number
        assignment.completion_percentage = min(100, int((compliance.week_number / protocol.duration_weeks) * 100))
        
        db.commit()
        
        return {"success": True}

@app.get("/api/compliance/{client_protocol_id}")
async def get_compliance(request: Request, client_protocol_id: int):
    """Get compliance logs for an assignment - UNIFIED system with detailed breakdown"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        assignment = db.query(ClientProtocol).filter(
            ClientProtocol.id == client_protocol_id,
            ClientProtocol.user_id == user_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        # Get the protocol to access its content
        protocol = db.query(Protocol).filter(Protocol.id == assignment.protocol_id).first()
        
        # Get ALL logs (both client and practitioner submissions)
        logs = db.execute(text("""
            SELECT 
                id,
                week_number,
                compliance_score,
                notes,
                compliance_data,
                image_base64,
                submitted_by,
                logged_at
            FROM compliance_logs
            WHERE client_protocol_id = :protocol_id
            ORDER BY logged_at DESC
        """), {'protocol_id': client_protocol_id}).fetchall()
        
        # Process each log to add detailed breakdown
        processed_logs = []
        for log in logs:
            log_dict = {
                "id": log[0],
                "week_number": log[1],
                "compliance_score": log[2],
                "notes": log[3],
                "compliance_data": log[4],
                "image_base64": log[5],
                "submitted_by": log[6] or 'practitioner',
                "logged_at": log[7].isoformat() if log[7] else None
            }
            
            # Calculate detailed breakdown if we have protocol and compliance_data
            if protocol and log[4]:  # log[4] is compliance_data
                breakdown = calculate_compliance_breakdown(protocol, log[4])
                log_dict.update(breakdown)
            
            processed_logs.append(log_dict)
        
        return {"logs": processed_logs}

# ── Outcome Tracking Endpoints ──────────────────────────────────────────────

@app.get("/api/outcomes/summary")
async def get_outcomes_summary(request: Request):
    """Practitioner dashboard: aggregate outcome stats for all their clients."""
    user_id = get_current_user_id(request)

    with get_db_context() as db:
        stats = db.execute(text("""
            SELECT
                COUNT(DISTINCT wc.client_protocol_id) AS clients_tracked,
                ROUND(AVG(wc.primary_symptom_rating), 1) AS avg_symptom,
                ROUND(AVG(wc.energy_level), 1) AS avg_energy,
                ROUND(AVG(wc.sleep_quality), 1) AS avg_sleep,
                COUNT(*) AS total_checkins
            FROM weekly_checkins wc
            JOIN client_protocols cp ON wc.client_protocol_id = cp.id
            JOIN protocols p ON cp.protocol_id = p.id
            WHERE p.user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        # Clients with improving trend (latest > first symptom rating)
        improving = db.execute(text("""
            WITH first_last AS (
                SELECT
                    client_protocol_id,
                    FIRST_VALUE(primary_symptom_rating) OVER (
                        PARTITION BY client_protocol_id ORDER BY submitted_at ASC
                    ) AS first_rating,
                    LAST_VALUE(primary_symptom_rating) OVER (
                        PARTITION BY client_protocol_id ORDER BY submitted_at ASC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) AS last_rating
                FROM weekly_checkins wc
                JOIN client_protocols cp ON wc.client_protocol_id = cp.id
                JOIN protocols p ON cp.protocol_id = p.id
                WHERE p.user_id = :user_id
            )
            SELECT
                COUNT(DISTINCT client_protocol_id) AS total,
                COUNT(DISTINCT CASE WHEN last_rating > first_rating THEN client_protocol_id END) AS improving
            FROM first_last
        """), {"user_id": user_id}).fetchone()

        # Per-protocol effectiveness
        protocol_stats = db.execute(text("""
            SELECT
                p.id AS protocol_id,
                p.name AS protocol_name,
                COUNT(DISTINCT wc.client_protocol_id) AS clients,
                ROUND(AVG(wc.primary_symptom_rating), 1) AS avg_symptom,
                ROUND(AVG(wc.energy_level), 1) AS avg_energy,
                ROUND(AVG(wc.sleep_quality), 1) AS avg_sleep,
                COUNT(*) AS total_checkins
            FROM weekly_checkins wc
            JOIN client_protocols cp ON wc.client_protocol_id = cp.id
            JOIN protocols p ON cp.protocol_id = p.id
            WHERE p.user_id = :user_id
            GROUP BY p.id, p.name
            ORDER BY avg_symptom DESC NULLS LAST
        """), {"user_id": user_id}).fetchall()

        clients_tracked = stats[0] if stats else 0
        total_clients = improving[0] if improving else 0
        improving_count = improving[1] if improving else 0
        pct_improving = round((improving_count / total_clients * 100), 0) if total_clients > 0 else 0

        return {
            "clients_tracked": clients_tracked,
            "total_checkins": stats[4] if stats else 0,
            "avg_symptom": float(stats[1]) if stats and stats[1] else 0,
            "avg_energy": float(stats[2]) if stats and stats[2] else 0,
            "avg_sleep": float(stats[3]) if stats and stats[3] else 0,
            "pct_improving": pct_improving,
            "protocols": [
                {
                    "id": row[0],
                    "name": row[1],
                    "clients": row[2],
                    "avg_symptom": float(row[3]) if row[3] else 0,
                    "avg_energy": float(row[4]) if row[4] else 0,
                    "avg_sleep": float(row[5]) if row[5] else 0,
                    "total_checkins": row[6]
                }
                for row in protocol_stats
            ]
        }

@app.get("/api/outcomes/{client_protocol_id}")
async def get_client_outcomes(request: Request, client_protocol_id: int):
    """Get all check-ins for a specific client protocol (practitioner view)."""
    user_id = get_current_user_id(request)

    with get_db_context() as db:
        # Verify ownership
        ownership = db.execute(text("""
            SELECT cp.id FROM client_protocols cp
            JOIN protocols p ON cp.protocol_id = p.id
            WHERE cp.id = :cp_id AND p.user_id = :user_id
        """), {"cp_id": client_protocol_id, "user_id": user_id}).fetchone()

        if not ownership:
            raise HTTPException(status_code=404, detail="Not found or unauthorized")

        checkins = db.execute(text("""
            SELECT id, week_number, primary_symptom_rating, energy_level,
                   sleep_quality, notes, what_helped, what_struggled, submitted_at
            FROM weekly_checkins
            WHERE client_protocol_id = :cp_id
            ORDER BY submitted_at ASC
        """), {"cp_id": client_protocol_id}).fetchall()

        return {
            "client_protocol_id": client_protocol_id,
            "checkins": [
                {
                    "id": row[0],
                    "week": row[1],
                    "symptom_rating": row[2],
                    "energy_level": row[3],
                    "sleep_quality": row[4],
                    "notes": row[5],
                    "what_helped": row[6],
                    "what_struggled": row[7],
                    "submitted_at": row[8].isoformat() if row[8] else None
                }
                for row in checkins
            ]
        }

# ─────────────────────────────────────────────────────────────────────────────

@app.delete("/api/compliance/{log_id}")

async def delete_compliance_log(request: Request, log_id: int):
    """Delete a specific compliance log entry"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Verify this log belongs to a protocol owned by this user
        log_check = db.execute(text("""
            SELECT cl.id 
            FROM compliance_logs cl
            JOIN client_protocols cp ON cl.client_protocol_id = cp.id
            WHERE cl.id = :log_id AND cp.user_id = :user_id
        """), {
            'log_id': log_id,
            'user_id': str(user_id)
        }).fetchone()
        
        if not log_check:
            raise HTTPException(status_code=404, detail="Compliance log not found")
        
        # Delete the log
        db.execute(text("""
            DELETE FROM compliance_logs WHERE id = :log_id
        """), {'log_id': log_id})
        
        db.commit()
        
        return {"success": True, "message": "Compliance log deleted"}


def calculate_compliance_breakdown(protocol, compliance_data):
    """Calculate detailed compliance breakdown from protocol and compliance_data"""
    if not compliance_data or not isinstance(compliance_data, dict):
        return {}
    
    categories = {
        'supplements': {'completed': 0, 'total': 0, 'percentage': 0},
        'nutrition': {'completed': 0, 'total': 0, 'percentage': 0},
        'exercises': {'completed': 0, 'total': 0, 'percentage': 0},
        'lifestyle': {'completed': 0, 'total': 0, 'percentage': 0},
        'timeline': {'completed': 0, 'total': 0, 'percentage': 0}
    }
    
    completed_items = []
    incomplete_items = []
    
    # Process supplements - match by INDEX (supplements-0, supplements-1, etc.)
    if protocol.supplements and isinstance(protocol.supplements, list):
        for idx, item in enumerate(protocol.supplements):
            if isinstance(item, dict):
                item_id = f"supplements-{idx}"
                item_name = item.get('name', f'Supplement {idx+1}')
                categories['supplements']['total'] += 1
                
                if compliance_data.get(item_id) == True:
                    categories['supplements']['completed'] += 1
                    completed_items.append({'text': item_name, 'category': 'supplements'})
                else:
                    incomplete_items.append({'text': item_name, 'category': 'supplements'})
    
    # Process nutrition - match by INDEX (nutrition-0, nutrition-1, etc.)
    if protocol.nutrition and isinstance(protocol.nutrition, dict):
        idx = 0
        if protocol.nutrition.get('foods_to_include'):
            item_id = f"nutrition-{idx}"
            categories['nutrition']['total'] += 1
            if compliance_data.get(item_id) == True:
                categories['nutrition']['completed'] += 1
                completed_items.append({'text': 'Include recommended foods', 'category': 'nutrition'})
            else:
                incomplete_items.append({'text': 'Include recommended foods', 'category': 'nutrition'})
            idx += 1
        
        if protocol.nutrition.get('foods_to_avoid'):
            item_id = f"nutrition-{idx}"
            categories['nutrition']['total'] += 1
            if compliance_data.get(item_id) == True:
                categories['nutrition']['completed'] += 1
                completed_items.append({'text': 'Avoid restricted foods', 'category': 'nutrition'})
            else:
                incomplete_items.append({'text': 'Avoid restricted foods', 'category': 'nutrition'})
            idx += 1
        
        if protocol.nutrition.get('meal_timing'):
            item_id = f"nutrition-{idx}"
            categories['nutrition']['total'] += 1
            if compliance_data.get(item_id) == True:
                categories['nutrition']['completed'] += 1
                completed_items.append({'text': 'Follow meal timing', 'category': 'nutrition'})
            else:
                incomplete_items.append({'text': 'Follow meal timing', 'category': 'nutrition'})
            idx += 1
        
        if protocol.nutrition.get('hydration'):
            item_id = f"nutrition-{idx}"
            categories['nutrition']['total'] += 1
            if compliance_data.get(item_id) == True:
                categories['nutrition']['completed'] += 1
                completed_items.append({'text': 'Meet hydration goals', 'category': 'nutrition'})
            else:
                incomplete_items.append({'text': 'Meet hydration goals', 'category': 'nutrition'})
            idx += 1
        
        if protocol.nutrition.get('daily_calories'):
            item_id = f"nutrition-{idx}"
            categories['nutrition']['total'] += 1
            if compliance_data.get(item_id) == True:
                categories['nutrition']['completed'] += 1
                completed_items.append({'text': 'Meet calorie target', 'category': 'nutrition'})
            else:
                incomplete_items.append({'text': 'Meet calorie target', 'category': 'nutrition'})
    
    # Process exercises - match by INDEX (exercises-0, exercises-1, etc.)
    if protocol.exercises and isinstance(protocol.exercises, list):
        for idx, item in enumerate(protocol.exercises):
            if isinstance(item, dict):
                item_id = f"exercises-{idx}"
                item_name = item.get('name', f'Exercise {idx+1}')
                categories['exercises']['total'] += 1
                
                if compliance_data.get(item_id) == True:
                    categories['exercises']['completed'] += 1
                    completed_items.append({'text': item_name, 'category': 'exercises'})
                else:
                    incomplete_items.append({'text': item_name, 'category': 'exercises'})
    
    # Process lifestyle_changes - match by INDEX (lifestyle-0, lifestyle-1, etc.)
    if protocol.lifestyle_changes and isinstance(protocol.lifestyle_changes, list):
        for idx, item in enumerate(protocol.lifestyle_changes):
            if isinstance(item, dict):
                item_id = f"lifestyle-{idx}"
                item_name = item.get('title', item.get('text', f'Lifestyle change {idx+1}'))
                categories['lifestyle']['total'] += 1
                
                if compliance_data.get(item_id) == True:
                    categories['lifestyle']['completed'] += 1
                    completed_items.append({'text': item_name, 'category': 'lifestyle'})
                else:
                    incomplete_items.append({'text': item_name, 'category': 'lifestyle'})
    
    # Process timeline/sleep - match by INDEX (timeline-0, timeline-1, etc.)
    if protocol.sleep and isinstance(protocol.sleep, dict):
        idx = 0
        if protocol.sleep.get('target_hours'):
            item_id = f"timeline-{idx}"
            categories['timeline']['total'] += 1
            if compliance_data.get(item_id) == True:
                categories['timeline']['completed'] += 1
                completed_items.append({'text': f"Sleep {protocol.sleep['target_hours']} hours", 'category': 'timeline'})
            else:
                incomplete_items.append({'text': f"Sleep {protocol.sleep['target_hours']} hours", 'category': 'timeline'})
            idx += 1
        
        if protocol.sleep.get('bedtime'):
            item_id = f"timeline-{idx}"
            categories['timeline']['total'] += 1
            if compliance_data.get(item_id) == True:
                categories['timeline']['completed'] += 1
                completed_items.append({'text': f"Bedtime by {protocol.sleep['bedtime']}", 'category': 'timeline'})
            else:
                incomplete_items.append({'text': f"Bedtime by {protocol.sleep['bedtime']}", 'category': 'timeline'})
    
    # Calculate percentages
    for category in categories.values():
        if category['total'] > 0:
            category['percentage'] = round((category['completed'] / category['total']) * 100)
    
    return {
        'category_breakdown': categories,
        'completed_items': completed_items,
        'incomplete_items': incomplete_items
    }
    
# ==================== PRO DASHBOARD ENDPOINTS ====================

@app.get("/api/pro/statistics")
async def get_pro_statistics(request: Request):
    """Get real-time dashboard statistics with period-over-period changes"""
    user_id = get_current_user_id(request)
    
    with engine.connect() as conn:
        # Current date boundaries
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_last_month = (start_of_month - timedelta(days=1)).replace(day=1)
        start_of_week = now - timedelta(days=now.weekday())
        start_of_last_week = start_of_week - timedelta(days=7)
        
        # TOTAL CLIENTS (from family_members table)
        current_clients = conn.execute(text("""
            SELECT COUNT(*) 
            FROM family_members
            WHERE user_id = :user_id
        """), {
            'user_id': str(user_id)
        }).scalar() or 0
        
        # Last month's client count
        last_month_clients = conn.execute(text("""
            SELECT COUNT(*) 
            FROM family_members
            WHERE user_id = :user_id
            AND created_at < :start_of_month
        """), {
            'user_id': str(user_id),
            'start_of_month': start_of_month
        }).scalar() or 0
        
        clients_change = current_clients - last_month_clients
        
        # TOTAL PROTOCOLS & ACTIVE COUNT
        total_protocols = conn.execute(text("""
            SELECT COUNT(*) 
            FROM protocols 
            WHERE user_id = :user_id
            AND is_active = true
        """), {'user_id': str(user_id)}).scalar() or 0
        
        active_protocols = conn.execute(text("""
            SELECT COUNT(*) 
            FROM client_protocols cp
            WHERE cp.user_id = :user_id
            AND cp.status = 'active'
        """), {'user_id': str(user_id)}).scalar() or 0
        
        # CONSULTATIONS (this week vs last week)
        current_consultations = conn.execute(text("""
            SELECT COUNT(*) 
            FROM client_messages 
            WHERE practitioner_id = :user_id
            AND created_at >= :start_of_week
        """), {
            'user_id': str(user_id),
            'start_of_week': start_of_week
        }).scalar() or 0
        
        last_week_consultations = conn.execute(text("""
            SELECT COUNT(*) 
            FROM client_messages 
            WHERE practitioner_id = :user_id
            AND created_at >= :start_of_last_week
            AND created_at < :start_of_week
        """), {
            'user_id': str(user_id),
            'start_of_last_week': start_of_last_week,
            'start_of_week': start_of_week
        }).scalar() or 0
        
        consultations_change = current_consultations - last_week_consultations
        
        # SUCCESS RATE (based on compliance scores)
        avg_compliance = conn.execute(text("""
            SELECT AVG(compliance_score) 
            FROM compliance_logs cl
            JOIN client_protocols cp ON cl.client_protocol_id = cp.id
            WHERE cp.user_id = :user_id
            AND cl.compliance_score IS NOT NULL
            AND cl.compliance_score > 0
        """), {'user_id': str(user_id)}).scalar()
        
        success_rate = round(avg_compliance) if avg_compliance else None
        
    return {
        'active_clients': current_clients,
        'clients_change': clients_change,
        'total_protocols': total_protocols,
        'protocols_active_count': active_protocols,
        'consultations': current_consultations,
        'consultations_change': consultations_change,
        'success_rate': success_rate
    }


@app.get("/api/pro/client-activity")
async def get_client_activity(request: Request):
    """Get recent client activity for dashboard table"""
    user_id = get_current_user_id(request)
    
    with engine.connect() as conn:
        activities = conn.execute(text("""
            SELECT 
                fm.id,
                fm.name as client_name,
                fm.relationship as email,
                fm.id as client_id,
                p.name as protocol_name,
                cp.current_week,
                p.duration_weeks as total_weeks,
                cp.completion_percentage as progress,
                GREATEST(
                    COALESCE(cm.last_message, cp.assigned_at),
                    COALESCE(cvt.last_accessed, cp.assigned_at),
                    COALESCE(cp.assigned_at, fm.created_at)
                ) as last_active,
                cp.id as assignment_id
            FROM family_members fm
            LEFT JOIN client_view_tokens cvt ON cvt.family_member_id = fm.id AND cvt.is_active = true
            LEFT JOIN client_protocols cp ON cp.client_id = fm.id AND cp.status = 'active'
            LEFT JOIN protocols p ON p.id = cp.protocol_id
            LEFT JOIN (
                SELECT family_member_id, MAX(created_at) as last_message
                FROM client_messages
                GROUP BY family_member_id
            ) cm ON cm.family_member_id = fm.id
            WHERE fm.user_id = :user_id
            ORDER BY last_active DESC
            LIMIT 50
        """), {'user_id': str(user_id)}).fetchall()
        
        return {
            'activities': [
                {
                    'id': row[0],
                    'client_name': row[1],
                    'email': row[2] or 'N/A',
                    'client_id': row[3],
                    'protocol_name': row[4] or 'No protocol assigned',
                    'current_week': row[5] or 0,
                    'total_weeks': row[6] or 0,
                    ''progress': row[7] or 0,
                    'assignment_id': row[9],
                    'last_active': row[8].isoformat() if row[8] else None
                }
                for row in activities
            ]
        }

@app.delete("/api/pro/client-activity/{activity_id}")
async def delete_client_activity(request: Request, activity_id: int):
    """Remove a client from the activity view (delete family member)"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Verify the family member belongs to this user
        member = db.query(FamilyMember).filter(
            FamilyMember.id == activity_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not member:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Delete related records first (in correct order)
        
        # 1. Delete compliance logs for this client's protocols
        db.execute(text("""
            DELETE FROM compliance_logs
            WHERE client_protocol_id IN (
                SELECT id FROM client_protocols WHERE client_id = :member_id
            )
        """), {'member_id': activity_id})
        
        # 2. Delete client protocol assignments
        db.execute(text("""
            DELETE FROM client_protocols WHERE client_id = :member_id
        """), {'member_id': activity_id})
        
        # 3. Delete client view tokens
        db.execute(text("""
            DELETE FROM client_view_tokens WHERE family_member_id = :member_id
        """), {'member_id': activity_id})
        
     # 4. Delete client messages
        db.execute(text("""
            DELETE FROM client_messages WHERE family_member_id = :member_id
        """), {'member_id': activity_id})
        
        # 5. Finally delete the family member
        db.delete(member)
        db.commit()
        
    return {"success": True, "message": "Client deleted successfully"}
    
SUBSCRIPTION_ADMIN_PASSWORD = os.getenv('SUBSCRIPTION_ADMIN_PASSWORD', 'Pootchi30')
# Add this endpoint
@app.post("/api/admin/activate-subscription")
async def admin_activate_subscription(request: Request):
    """Admin endpoint to manually activate subscriptions"""
    try:
        data = await request.json()
        admin_password = data.get('admin_password')
        user_email = data.get('email')
        tier = data.get('tier')
        
        # Verify admin password
        if admin_password != SUBSCRIPTION_ADMIN_PASSWORD:
            raise HTTPException(status_code=403, detail="Invalid admin password")
        
        # Validate tier
        if tier not in ['free', 'basic', 'premium', 'pro']:
            raise HTTPException(status_code=400, detail="Invalid tier")
        
        # Update user subscription
        with get_db_context() as db:
            user = db.query(User).filter(User.email == user_email).first()
            
            if not user:
                raise HTTPException(status_code=404, detail=f"User not found: {user_email}")
            
            # Set subscription details
            user.subscription_tier = tier
            user.subscription_status = 'active'
            
            # Set family member limits
            if tier == 'basic':
                user.family_member_limit = 1
            elif tier == 'premium':
                user.family_member_limit = 5
            elif tier == 'pro':
                user.family_member_limit = 999
            else:  # free
                user.family_member_limit = 0
            
            db.commit()
            
            return {
                "success": True,
                "message": f"✅ {user_email} activated with {tier.upper()} tier",
                "user": {
                    "email": user.email,
                    "tier": user.subscription_tier,
                    "family_limit": user.family_member_limit
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Admin activation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/deactivate-subscription")
async def admin_deactivate_subscription(request: Request):
    """Admin endpoint to deactivate subscriptions"""
    try:
        data = await request.json()
        admin_password = data.get('admin_password')
        user_email = data.get('email')
        
        # Verify admin password
        if admin_password != SUBSCRIPTION_ADMIN_PASSWORD:
            raise HTTPException(status_code=403, detail="Invalid admin password")
        
        with get_db_context() as db:
            user = db.query(User).filter(User.email == user_email).first()
            
            if not user:
                raise HTTPException(status_code=404, detail=f"User not found: {user_email}")
            
            # Reset to free tier
            user.subscription_tier = 'free'
            user.subscription_status = 'inactive'
            user.family_member_limit = 0
            
            db.commit()
            
            return {
                "success": True,
                "message": f"✅ {user_email} deactivated (reverted to FREE)",
                "user": {
                    "email": user.email,
                    "tier": user.subscription_tier
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Admin deactivation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/delete-user")
async def delete_user(data: dict):
    """Permanently delete a user and all their data"""
    admin_password = data.get('admin_password')
    email = data.get('email', '').strip().lower()
    
    # Verify admin password
    if admin_password != SUBSCRIPTION_ADMIN_PASSWORD:  # ← CHANGED
        raise HTTPException(status_code=403, detail="Invalid admin password")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    with get_db_context() as db:
        # Check if user exists
        user = db.execute(text("""
            SELECT id, email, subscription_tier FROM users WHERE email = :email
        """), {'email': email}).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user[0])
        
        # Delete user (CASCADE will handle related records)
        db.execute(text("""
            DELETE FROM users WHERE id = :user_id
        """), {'user_id': user_id})
        
        db.commit()
        
        print(f"🗑️ DELETED USER: {email} (ID: {user_id})")
        
        return {
            "success": True,
            "message": f"User {email} permanently deleted"
        }


@app.get("/api/admin/list-users")
async def admin_list_users(request: Request, admin_password: str):
    """Admin endpoint to list all users and their subscriptions"""
    try:
        # Verify admin password
        if admin_password != SUBSCRIPTION_ADMIN_PASSWORD:
            raise HTTPException(status_code=403, detail="Invalid admin password")
        
        with get_db_context() as db:
            users = db.query(User).all()
            
            user_list = []
            for user in users:  # ← FIXED: removed duplicate line
                user_list.append({
                    "email": user.email,
                    "tier": user.subscription_tier or 'free',
                    "status": getattr(user, 'subscription_status', 'active') if user.subscription_tier and user.subscription_tier != 'free' else 'inactive',
                    "family_limit": user.family_member_limit or 0,
                    "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
                })
            
            return {
                "success": True,
                "total_users": len(user_list),
                "users": user_list
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Admin list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
