# app/database.py
"""
Enhanced database module with subscription features
Compatible with existing main.py imports
INCLUDES AUTO-FIX FOR HEALTH_PROFILES COLUMNS

✅ UPDATED FOR FAMILY ACCOUNTS FEATURE
-------------------------------------------
Changes made:
1. FamilyMember model updated:
   - ID changed from Integer to String (for UUID compatibility)
   - relation_type renamed to 'relationship' (API consistency)
   - Added: date_of_birth, notes, health_profile_id, conversation_count, updated_at
   - Added relationship to HealthProfile

2. HealthProfile model updated:
   - Added: family_member_id (link to family member)
   - Added: blood_type, family_history
   - Added relationship to FamilyMember

MIGRATION REQUIRED:
Run this SQL on your database:

-- 1. Update family_members table structure
ALTER TABLE family_members 
  ALTER COLUMN id TYPE VARCHAR,
  ADD COLUMN IF NOT EXISTS relationship VARCHAR,
  ADD COLUMN IF NOT EXISTS date_of_birth DATE,
  ADD COLUMN IF NOT EXISTS notes TEXT,
  ADD COLUMN IF NOT EXISTS health_profile_id VARCHAR,
  ADD COLUMN IF NOT EXISTS conversation_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Update existing data: copy relation_type to relationship
UPDATE family_members SET relationship = relation_type WHERE relationship IS NULL;

-- Drop old column (optional - only if you don't need it)
-- ALTER TABLE family_members DROP COLUMN IF EXISTS relation_type;
-- ALTER TABLE family_members DROP COLUMN IF EXISTS health_notes;

-- 2. Update health_profiles table
ALTER TABLE health_profiles
  ADD COLUMN IF NOT EXISTS family_member_id VARCHAR,
  ADD COLUMN IF NOT EXISTS blood_type VARCHAR,
  ADD COLUMN IF NOT EXISTS family_history TEXT;

-- 3. Add foreign key constraints
ALTER TABLE family_members 
  ADD CONSTRAINT fk_family_member_health_profile 
  FOREIGN KEY (health_profile_id) REFERENCES health_profiles(id) ON DELETE SET NULL;

ALTER TABLE health_profiles
  ADD CONSTRAINT fk_health_profile_family_member
  FOREIGN KEY (family_member_id) REFERENCES family_members(id) ON DELETE SET NULL;

"""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/treeoflife")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ============================================================================
# MODELS
# ============================================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Subscription fields
    subscription_tier = Column(String, default="free")  # free, premium, pro
    subscription_status = Column(String, default="active")  # active, cancelled, expired
    subscription_expires_at = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    
    # Usage tracking
    messages_this_month = Column(Integer, default=0)
    messages_reset_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    symptoms = relationship("Symptom", back_populates="user", cascade="all, delete-orphan")
    treatments = relationship("Treatment", back_populates="user", cascade="all, delete-orphan")
    family_members = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan")
    custom_protocols = relationship("CustomProtocol", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)  # UUID type
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    preview = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # ✅ FAMILY MEMBER LINK (NEW)
    family_member_id = Column(String, ForeignKey("family_members.id"), nullable=True)
    
    # Basic info
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    blood_type = Column(String, nullable=True)  # ✅ NEW FIELD
    
    # Constitutional types
    ayurvedic_dosha = Column(String, nullable=True)  # vata, pitta, kapha, combinations
    tcm_pattern = Column(String, nullable=True)
    body_type = Column(String, nullable=True)
    
    # Tradition preferences (main.py expects this as a direct column!)
    preferred_traditions = Column(JSON, default=list, nullable=True)
    
    # Health data (stored as JSON)
    current_conditions = Column(JSON, default=list)
    medications = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    past_diagnoses = Column(JSON, default=list, nullable=True)  # main.py expects this!
    health_goals = Column(JSON, default=list, nullable=True)  # main.py expects this!
    
    # Lifestyle data (main.py expects these as direct columns!)
    diet_type = Column(String, nullable=True)
    exercise_frequency = Column(String, nullable=True)
    sleep_hours = Column(Integer, nullable=True)
    stress_level = Column(Integer, nullable=True)  # 1-10 scale
    
    # Treatment philosophy (main.py expects this!)
    treatment_philosophy = Column(String, nullable=True)
    
    # Family history (NEW FIELD) ✅
    family_history = Column(Text, nullable=True)
    
    # Legacy lifestyle/preferences (keep for compatibility)
    lifestyle = Column(JSON, default=dict)
    preferences = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="health_profile")
    family_member = relationship("FamilyMember", back_populates="health_profile", uselist=False)  # ✅ NEW RELATIONSHIP


class Symptom(Base):
    __tablename__ = "symptoms"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    severity = Column(Integer, nullable=True)  # 1-10
    description = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="symptoms")


class Treatment(Base):
    __tablename__ = "treatments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)  # herb, supplement, food, exercise, etc.
    dosage = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="treatments")


class FamilyMember(Base):
    """Family member model for Premium/Pro users"""
    __tablename__ = "family_members"
    
    # ✅ UPDATED: String ID to match main.py (uses uuid.uuid4() as string)
    id = Column(String, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Basic info
    name = Column(String, nullable=False)
    relationship = Column(String, nullable=False)  # ✅ RENAMED from relation_type to match API
    age = Column(Integer, nullable=True)
    date_of_birth = Column(Date, nullable=True)  # ✅ NEW FIELD
    gender = Column(String, nullable=True)
    notes = Column(Text, nullable=True)  # ✅ CHANGED from JSON to Text
    
    # Health profile link
    health_profile_id = Column(String, ForeignKey("health_profiles.id"), nullable=True)  # ✅ NEW FIELD
    
    # Tracking
    conversation_count = Column(Integer, default=0)  # ✅ NEW FIELD
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # ✅ NEW FIELD
    
    # Relationships
    user = relationship("User", back_populates="family_members")
    health_profile = relationship("HealthProfile", back_populates="family_member", uselist=False)  # ✅ NEW RELATIONSHIP


class CustomProtocol(Base):
    __tablename__ = "custom_protocols"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    protocol_data = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="custom_protocols")


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_database():
    """Initialize database - creates all tables (compatible with main.py)"""
    print("🔧 Initializing database...")
    
    # First, fix any broken tables BEFORE creating
    drop_broken_tables()
    
    # Then create all tables (will recreate any dropped ones)
    print("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    
    # Finally, add any missing columns to existing tables
    add_missing_columns()


def drop_broken_tables():
    """Drop any tables that have broken schemas (like missing autoincrement)"""
    print("🔍 Checking for broken tables...")
    
    try:
        from sqlalchemy import text, inspect
        
        with engine.connect() as conn:
            inspector = inspect(engine)
            
            # Check if health_profiles exists and has broken ID
            if 'health_profiles' in inspector.get_table_names():
                try:
                    result = conn.execute(text("""
                        SELECT column_default 
                        FROM information_schema.columns 
                        WHERE table_name = 'health_profiles' 
                        AND column_name = 'id';
                    """))
                    row = result.fetchone()
                    
                    # If column_default is NULL, the ID doesn't autoincrement - DROP IT!
                    if row and row[0] is None:
                        print("  ⚠️  health_profiles.id is broken (no autoincrement)")
                        print("  🗑️  Dropping health_profiles table...")
                        conn.execute(text("DROP TABLE health_profiles CASCADE;"))
                        conn.commit()
                        print("  ✅ Broken table dropped - will be recreated")
                    else:
                        print("  ✅ health_profiles table is OK")
                except Exception as e:
                    print(f"  ℹ️  Could not check health_profiles: {e}")
            else:
                print("  ℹ️  health_profiles doesn't exist yet (will be created)")
            
            # Check if messages exists and has broken ID
            if 'messages' in inspector.get_table_names():
                try:
                    result = conn.execute(text("""
                        SELECT column_default 
                        FROM information_schema.columns 
                        WHERE table_name = 'messages' 
                        AND column_name = 'id';
                    """))
                    row = result.fetchone()
                    
                    # If column_default is NULL, the ID doesn't autoincrement - DROP IT!
                    if row and row[0] is None:
                        print("  ⚠️  messages.id is broken (no autoincrement)")
                        print("  🗑️  Dropping messages table...")
                        conn.execute(text("DROP TABLE messages CASCADE;"))
                        conn.commit()
                        print("  ✅ Broken table dropped - will be recreated")
                    else:
                        print("  ✅ messages table is OK")
                except Exception as e:
                    print(f"  ℹ️  Could not check messages: {e}")
            else:
                print("  ℹ️  messages doesn't exist yet (will be created)")
            
            # Check if conversations exists and has broken ID (it uses string ID, so skip this check)
            # Conversations uses UUID for id, not autoincrement, so it's fine
                
    except Exception as e:
        print(f"  ⚠️  Table check failed: {e}")


def add_missing_columns():
    """Add any missing columns to existing tables"""
    print("🔍 Checking for missing columns...")
    
    try:
        from sqlalchemy import text, inspect
        
        with engine.connect() as conn:
            inspector = inspect(engine)
            
            # ===================================================================
            # FIX USERS TABLE
            # ===================================================================
            if 'users' in inspector.get_table_names():
                existing_columns = [col['name'] for col in inspector.get_columns('users')]
                print(f"  ℹ️  Found {len(existing_columns)} existing columns in users table")
                
                # List of all required columns with their types
                required_columns = {
                    'name': 'VARCHAR',
                    'subscription_tier': "VARCHAR DEFAULT 'free'",
                    'subscription_status': "VARCHAR DEFAULT 'active'",
                    'subscription_expires_at': 'TIMESTAMP',
                    'stripe_customer_id': 'VARCHAR',
                    'stripe_subscription_id': 'VARCHAR',
                    'messages_this_month': 'INTEGER DEFAULT 0',
                    'messages_reset_date': 'TIMESTAMP DEFAULT NOW()'
                }
                
                # Add any missing columns
                columns_added = 0
                for col_name, col_type in required_columns.items():
                    if col_name not in existing_columns:
                        print(f"  📝 Adding missing '{col_name}' column to users table...")
                        conn.execute(text(f"""
                            ALTER TABLE users ADD COLUMN {col_name} {col_type};
                        """))
                        columns_added += 1
                        print(f"  ✅ '{col_name}' column added!")
                
                if columns_added > 0:
                    conn.commit()
                    print(f"  🎉 Added {columns_added} missing column(s) to users table!")
                else:
                    print("  ✅ Users table - all columns present")
            else:
                print("  ℹ️  Users table doesn't exist yet (will be created)")
            
            # ===================================================================
            # FIX HEALTH_PROFILES TABLE - THIS IS THE NEW FIX!
            # ===================================================================
            if 'health_profiles' in inspector.get_table_names():
                existing_columns = [col['name'] for col in inspector.get_columns('health_profiles')]
                print(f"  ℹ️  Found {len(existing_columns)} existing columns in health_profiles table")
                
                # List of all required columns with their types
                required_columns = {
                    'age': 'INTEGER',
                    'gender': 'VARCHAR',
                    'height': 'DOUBLE PRECISION',  # Float in PostgreSQL
                    'weight': 'DOUBLE PRECISION',  # Float in PostgreSQL
                    'ayurvedic_dosha': 'VARCHAR',
                    'tcm_pattern': 'VARCHAR',
                    'body_type': 'VARCHAR',
                    'preferred_traditions': 'JSON',  # main.py expects this!
                    'current_conditions': 'JSON',
                    'medications': 'JSON',
                    'allergies': 'JSON',
                    'past_diagnoses': 'JSON',  # main.py expects this!
                    'health_goals': 'JSON',  # main.py expects this!
                    'diet_type': 'VARCHAR',  # main.py expects this!
                    'exercise_frequency': 'VARCHAR',  # main.py expects this!
                    'sleep_hours': 'INTEGER',  # main.py expects this!
                    'stress_level': 'INTEGER',  # main.py expects this!
                    'treatment_philosophy': 'VARCHAR',  # main.py expects this!
                    'lifestyle': 'JSON',
                    'preferences': 'JSON'
                }
                
                # Add any missing columns
                columns_added = 0
                for col_name, col_type in required_columns.items():
                    if col_name not in existing_columns:
                        print(f"  📝 Adding missing '{col_name}' column to health_profiles table...")
                        conn.execute(text(f"""
                            ALTER TABLE health_profiles ADD COLUMN {col_name} {col_type};
                        """))
                        columns_added += 1
                        print(f"  ✅ '{col_name}' column added!")
                
                if columns_added > 0:
                    conn.commit()
                    print(f"  🎉 Added {columns_added} missing column(s) to health_profiles table!")
                else:
                    print("  ✅ Health_profiles table - all columns present")
            else:
                print("  ℹ️  Health_profiles table doesn't exist yet (will be created)")
            
            # ===================================================================
            # FIX CONVERSATIONS TABLE
            # ===================================================================
            if 'conversations' in inspector.get_table_names():
                existing_columns = [col['name'] for col in inspector.get_columns('conversations')]
                print(f"  ℹ️  Found {len(existing_columns)} existing columns in conversations table")
                
                # List of all required columns with their types
                required_columns = {
                    'preview': 'TEXT'  # main.py needs this!
                }
                
                # Add any missing columns
                columns_added = 0
                for col_name, col_type in required_columns.items():
                    if col_name not in existing_columns:
                        print(f"  📝 Adding missing '{col_name}' column to conversations table...")
                        conn.execute(text(f"""
                            ALTER TABLE conversations ADD COLUMN {col_name} {col_type};
                        """))
                        columns_added += 1
                        print(f"  ✅ '{col_name}' column added!")
                
                if columns_added > 0:
                    conn.commit()
                    print(f"  🎉 Added {columns_added} missing column(s) to conversations table!")
                else:
                    print("  ✅ Conversations table - all columns present")
            else:
                print("  ℹ️  Conversations table doesn't exist yet (will be created)")
            
            # ===================================================================
            # FIX MESSAGES TABLE
            # ===================================================================
            if 'messages' in inspector.get_table_names():
                existing_columns = [col['name'] for col in inspector.get_columns('messages')]
                print(f"  ℹ️  Found {len(existing_columns)} existing columns in messages table")
                
                # List of all required columns with their types
                required_columns = {
                    'timestamp': 'TIMESTAMP DEFAULT NOW()'  # main.py needs this!
                }
                
                # Add any missing columns
                columns_added = 0
                for col_name, col_type in required_columns.items():
                    if col_name not in existing_columns:
                        print(f"  📝 Adding missing '{col_name}' column to messages table...")
                        conn.execute(text(f"""
                            ALTER TABLE messages ADD COLUMN {col_name} {col_type};
                        """))
                        columns_added += 1
                        print(f"  ✅ '{col_name}' column added!")
                
                if columns_added > 0:
                    conn.commit()
                    print(f"  🎉 Added {columns_added} missing column(s) to messages table!")
                else:
                    print("  ✅ Messages table - all columns present")
            else:
                print("  ℹ️  Messages table doesn't exist yet (will be created)")
                
    except Exception as e:
        print(f"  ⚠️  Column check failed (non-fatal): {e}")
        print("  ℹ️  Continuing anyway...")
        import traceback
        traceback.print_exc()


# Alias for backward compatibility
init_db = init_database


def test_connection():
    """Test database connection"""
    try:
        engine.connect()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def create_admin_user():
    """Create admin user if doesn't exist"""
    print("👤 Creating admin user...")
    
    try:
        with get_db_context() as db:
            # Check if admin already exists
            admin_email = os.getenv("ADMIN_EMAIL", "admin@treeoflife.com")
            existing_admin = db.query(User).filter(User.email == admin_email).first()
            
            if existing_admin:
                print(f"  ℹ️  Admin user '{admin_email}' already exists")
                return existing_admin
            
            # Create new admin
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            admin_password = os.getenv("ADMIN_PASSWORD", "changeme123")
            
            admin = User(
                email=admin_email,
                name="Admin",
                password_hash=pwd_context.hash(admin_password),
                is_active=True,
                subscription_tier="pro",
                subscription_status="active"
            )
            
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
            print(f"  ✅ Admin user created: {admin_email}")
            print(f"  ℹ️  Password: {admin_password}")
            return admin
            
    except Exception as e:
        print(f"  ⚠️  Admin user creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# HELPER FUNCTIONS (ALL FUNCTIONS MAIN.PY NEEDS)
# ============================================================================

def get_db_session():
    """Get database session (alias for get_db for compatibility)"""
    return get_db()


def create_user(db: Session, email: str, password_hash: str, name: str = None) -> User:
    """Create new user"""
    user = User(
        email=email,
        password_hash=password_hash,
        name=name,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_conversation(db: Session, conversation_id: str, user_id: uuid.UUID, title: str = None, preview: str = None) -> Conversation:
    """Create new conversation with title and preview"""
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    if not title:
        title = "New Conversation"
    
    if not preview:
        preview = ""
    
    # Convert string UUID to UUID object if needed
    if isinstance(conversation_id, str):
        conversation_id = uuid.UUID(conversation_id)
    
    conversation = Conversation(
        id=conversation_id,
        user_id=user_id,
        title=title,
        preview=preview,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    """Get conversation by ID"""
    # Convert string UUID to UUID object if needed
    if isinstance(conversation_id, str):
        conversation_id = uuid.UUID(conversation_id)
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_user_conversations(db: Session, user_id: uuid.UUID) -> List[Conversation]:
    """Get all conversations for a user"""
    return db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.updated_at.desc()).all()


def add_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    """Add message to conversation"""
    # Convert string UUID to UUID object if needed
    if isinstance(conversation_id, str):
        conversation_id = uuid.UUID(conversation_id)
    
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        timestamp=datetime.utcnow()
    )
    db.add(message)
    
    # Update conversation timestamp
    conversation = get_conversation(db, conversation_id)
    if conversation:
        conversation.updated_at = datetime.utcnow()
        # Update preview with first 100 chars of latest user message
        if role == "user":
            conversation.preview = content[:100]
    
    db.commit()
    db.refresh(message)
    return message


def delete_conversation(db: Session, conversation_id: str) -> bool:
    """Delete conversation and all its messages"""
    conversation = get_conversation(db, conversation_id)
    if conversation:
        db.delete(conversation)
        db.commit()
        return True
    return False


def update_health_profile(db: Session, user_id: uuid.UUID, **profile_data) -> HealthProfile:
    """Update health profile - accepts keyword arguments"""
    profile = get_or_create_health_profile(db, user_id)
    
    # Update fields
    for key, value in profile_data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


def get_or_create_health_profile(db: Session, user_id: uuid.UUID) -> HealthProfile:
    """Get existing health profile or create new one"""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    
    if not profile:
        profile = HealthProfile(
            user_id=user_id,
            preferred_traditions=[],  # Initialize empty list for traditions
            current_conditions=[],
            medications=[],
            allergies=[],
            past_diagnoses=[],  # Initialize for main.py
            health_goals=[],  # Initialize for main.py
            lifestyle={},
            preferences={}
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    return profile


def check_message_limit(user: User) -> dict:
    """Check if user has exceeded message limit"""
    # Free tier: 10 messages per month
    # Premium/Pro: Unlimited
    
    if user.subscription_tier in ['premium', 'pro']:
        return {"allowed": True, "remaining": -1}  # Unlimited
    
    # Check if we need to reset the counter
    now = datetime.utcnow()
    if user.messages_reset_date < now - timedelta(days=30):
        user.messages_this_month = 0
        user.messages_reset_date = now
    
    # Check limit
    limit = 10
    remaining = limit - user.messages_this_month
    
    return {
        "allowed": remaining > 0,
        "remaining": max(0, remaining),
        "limit": limit
    }


def increment_message_count(db: Session, user_id: uuid.UUID):
    """Increment user's message count"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.messages_this_month += 1
        db.commit()


def update_user_subscription(
    db: Session,
    user_id: uuid.UUID,
    tier: str,
    status: str,
    expires_at: Optional[datetime] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None
):
    """Update user's subscription details"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if user:
        user.subscription_tier = tier
        user.subscription_status = status
        user.subscription_expires_at = expires_at
        
        if stripe_customer_id:
            user.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            user.stripe_subscription_id = stripe_subscription_id
        
        db.commit()
        db.refresh(user)
        
        return user
    
    return None


def get_user_by_stripe_customer(db: Session, stripe_customer_id: str) -> Optional[User]:
    """Get user by Stripe customer ID"""
    return db.query(User).filter(User.stripe_customer_id == stripe_customer_id).first()


# ============================================================================
# EXPORT ALL NECESSARY ITEMS
# ============================================================================

__all__ = [
    # Core
    'Base',
    'engine',
    'SessionLocal',
    'get_db',
    'get_db_session',
    'get_db_context',
    'init_database',
    'init_db',
    'test_connection',
    'create_admin_user',
    # Models
    'User',
    'Conversation',
    'Message',
    'HealthProfile',
    'Symptom',
    'Treatment',
    'FamilyMember',
    'CustomProtocol',
    # User functions
    'create_user',
    'get_user_by_email',
    'get_user_by_id',
    # Conversation functions
    'create_conversation',
    'get_conversation',
    'get_user_conversations',
    'add_message',
    'delete_conversation',
    # Health profile functions
    'get_or_create_health_profile',
    'update_health_profile',
    # Subscription functions
    'check_message_limit',
    'increment_message_count',
    'update_user_subscription',
    'get_user_by_stripe_customer',
]
