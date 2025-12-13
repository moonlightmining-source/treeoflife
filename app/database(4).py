# app/database.py
"""
Enhanced database module with subscription features
Compatible with existing main.py imports
"""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
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
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
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
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic info
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    
    # Constitutional types
    ayurvedic_dosha = Column(String, nullable=True)  # vata, pitta, kapha, combinations
    tcm_pattern = Column(String, nullable=True)
    body_type = Column(String, nullable=True)
    
    # Health data (stored as JSON)
    current_conditions = Column(JSON, default=list)
    medications = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    lifestyle = Column(JSON, default=dict)
    preferences = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="health_profile")


class Symptom(Base):
    __tablename__ = "symptoms"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
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
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    treatment_type = Column(String, nullable=True)  # herb, supplement, food, practice
    tradition = Column(String, nullable=True)  # ayurveda, tcm, western, etc.
    dosage = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="treatments")


class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    member_relationship = Column(String, nullable=False)  # RENAMED from 'relationship'
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True)
    
    # Health profile data for this family member (JSON)
    health_profile_data = Column(JSON, default=dict)
    
    is_active = Column(Boolean, default=False)  # Is this the currently active profile?
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="family_members")
    
    def to_dict(self):
        """Convert to dict for API responses - use 'relationship' for backward compatibility"""
        return {
            'id': self.id,
            'name': self.name,
            'relationship': self.member_relationship,  # Return as 'relationship' for API
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'health_profile': self.health_profile_data,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class CustomProtocol(Base):
    __tablename__ = "custom_protocols"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    traditions = Column(JSON, default=list)  # Which traditions used
    steps = Column(JSON, default=list)  # Protocol steps
    duration_weeks = Column(Integer, nullable=True)
    tags = Column(JSON, default=list)
    condition = Column(String, nullable=True)  # What it treats
    
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="custom_protocols")


class ClientRecord(Base):
    __tablename__ = "client_records"
    
    id = Column(Integer, primary_key=True, index=True)
    practitioner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    client_name = Column(String, nullable=False)
    client_email = Column(String, nullable=True)
    constitution = Column(String, nullable=True)
    active_protocol_id = Column(Integer, ForeignKey("custom_protocols.id"), nullable=True)
    notes = Column(Text, nullable=True)
    
    last_session = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# DATABASE FUNCTIONS (Compatible with main.py)
# ============================================================================

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias for backward compatibility
get_db_session = get_db
get_session = get_db  # Another common alias


@contextmanager
def get_db_context():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias for context manager
db_context = get_db_context


def init_database():
    """Initialize database - creates all tables (compatible with main.py)"""
    print("🔧 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


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
    admin_email = os.getenv("ADMIN_EMAIL", "moonlight_mining@yahoo.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "changeme123")
    
    with get_db_context() as db:
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            admin = User(
                email=admin_email,
                password_hash=pwd_context.hash(admin_password),
                subscription_tier="pro",  # Give admin pro access
                is_active=True
            )
            db.add(admin)
            db.commit()
            print(f"✅ Admin user created: {admin_email}")
        else:
            print(f"ℹ️  Admin user already exists: {admin_email}")


# ============================================================================
# USER CRUD FUNCTIONS
# ============================================================================

def create_user(db: Session, email: str, name: str, password_hash: str) -> User:
    """Create a new user"""
    user = User(
        email=email,
        name=name,
        password_hash=password_hash
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, data: dict) -> Optional[User]:
    """Update user data"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        for key, value in data.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete user (soft delete - set is_active=False)"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = False
        db.commit()
        return True
    return False


# ============================================================================
# CONVERSATION CRUD FUNCTIONS
# ============================================================================

def create_conversation(db: Session, conversation_id: str, user_id: int, title: str, preview: str) -> Conversation:
    """Create a new conversation"""
    conversation = Conversation(
        id=conversation_id,
        user_id=user_id,
        title=title,
        preview=preview
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversations(db: Session, user_id: int) -> List[Conversation]:
    """Get all conversations for a user"""
    return db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).all()


# Alias for compatibility
get_user_conversations = get_conversations


def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    """Get conversation by ID"""
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def delete_conversation(db: Session, conversation_id: str) -> bool:
    """Delete conversation"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        db.delete(conversation)
        db.commit()
        return True
    return False


# ============================================================================
# MESSAGE CRUD FUNCTIONS
# ============================================================================

def create_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    """Create a new message"""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


# Alias for compatibility
add_message = create_message


def get_messages(db: Session, conversation_id: str) -> List[Message]:
    """Get all messages in a conversation"""
    return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()


# ============================================================================
# HEALTH PROFILE CRUD FUNCTIONS
# ============================================================================

def create_health_profile(db: Session, user_id: int, data: dict) -> HealthProfile:
    """Create or update health profile"""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    if profile:
        # Update existing
        for key, value in data.items():
            setattr(profile, key, value)
    else:
        # Create new
        profile = HealthProfile(user_id=user_id, **data)
        db.add(profile)
    
    db.commit()
    db.refresh(profile)
    return profile


def get_health_profile(db: Session, user_id: int) -> Optional[HealthProfile]:
    """Get health profile for user"""
    return db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()


def get_or_create_health_profile(db: Session, user_id: int) -> HealthProfile:
    """Get health profile for user, or create if doesn't exist"""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    if not profile:
        profile = HealthProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_health_profile(db: Session, user_id: int, **kwargs) -> HealthProfile:
    """Update health profile with provided fields"""
    profile = get_or_create_health_profile(db, user_id)
    
    for key, value in kwargs.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    return profile


# ============================================================================
# SUBSCRIPTION HELPER FUNCTIONS
# ============================================================================

def check_message_limit(user: User) -> dict:
    """Check if user has reached message limit"""
    # Premium and Pro have unlimited messages
    if user.subscription_tier in ['premium', 'pro']:
        return {'allowed': True, 'remaining': 'unlimited'}
    
    # Free tier: 10 messages per month
    FREE_TIER_LIMIT = 10
    
    # Reset counter if new month
    now = datetime.utcnow()
    if user.messages_reset_date.month != now.month or user.messages_reset_date.year != now.year:
        user.messages_this_month = 0
        user.messages_reset_date = now
    
    if user.messages_this_month >= FREE_TIER_LIMIT:
        return {
            'allowed': False,
            'remaining': 0,
            'limit': FREE_TIER_LIMIT,
            'reset_date': user.messages_reset_date.replace(month=user.messages_reset_date.month + 1, day=1)
        }
    
    return {
        'allowed': True,
        'remaining': FREE_TIER_LIMIT - user.messages_this_month,
        'limit': FREE_TIER_LIMIT
    }


def increment_message_count(user: User, db: Session):
    """Increment user's message count"""
    user.messages_this_month += 1
    db.commit()


def get_family_members(user_id: int, db: Session) -> List[FamilyMember]:
    """Get all family members for a user"""
    return db.query(FamilyMember).filter(FamilyMember.user_id == user_id).all()


def create_family_member(user_id: int, data: dict, db: Session) -> FamilyMember:
    """Create a new family member"""
    member = FamilyMember(
        user_id=user_id,
        name=data['name'],
        member_relationship=data.get('relationship', 'other'),
        date_of_birth=data.get('date_of_birth'),
        gender=data.get('gender'),
        health_profile_data=data.get('health_profile', {})
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def switch_active_profile(user_id: int, member_id: int, db: Session) -> bool:
    """Switch active family profile"""
    # Deactivate all profiles
    db.query(FamilyMember).filter(FamilyMember.user_id == user_id).update({'is_active': False})
    
    # Activate selected profile
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.user_id == user_id
    ).first()
    
    if member:
        member.is_active = True
        db.commit()
        return True
    return False


def get_active_family_member(user_id: int, db: Session) -> Optional[FamilyMember]:
    """Get the currently active family member"""
    return db.query(FamilyMember).filter(
        FamilyMember.user_id == user_id,
        FamilyMember.is_active == True
    ).first()


# ============================================================================
# EXPORTS - All importable items
# ============================================================================

__all__ = [
    # Database objects
    'Base',
    'engine',
    'SessionLocal',
    
    # Session functions
    'get_db',
    'get_db_session',
    'get_session',
    'get_db_context',
    'db_context',
    
    # Initialization
    'init_database',
    'init_db',
    'test_connection',
    'create_admin_user',
    'startup_database',
    'shutdown_database',
    
    # Models
    'User',
    'Conversation',
    'Message',
    'HealthProfile',
    'Symptom',
    'Treatment',
    'FamilyMember',
    'CustomProtocol',
    'ClientRecord',
    
    # User CRUD
    'create_user',
    'get_user_by_email',
    'get_user_by_id',
    'update_user',
    'delete_user',
    
    # Conversation CRUD
    'create_conversation',
    'get_conversations',
    'get_user_conversations',
    'get_conversation',
    'delete_conversation',
    
    # Message CRUD
    'create_message',
    'add_message',
    'get_messages',
    
    # Health Profile CRUD
    'create_health_profile',
    'get_health_profile',
    'get_or_create_health_profile',
    'update_health_profile',
    
    # Subscription helpers
    'check_message_limit',
    'increment_message_count',
    
    # Family helpers
    'get_family_members',
    'create_family_member',
    'switch_active_profile',
    'get_active_family_member',
]


# ============================================================================
# STARTUP FUNCTIONS
# ============================================================================

async def startup_database():
    """Async startup for FastAPI"""
    print("🚀 Starting Tree of Life AI...")
    print("📊 Testing database connection...")
    
    if not test_connection():
        raise Exception("Database connection failed!")
    
    print("✅ Database connection successful!")
    init_database()
    create_admin_user()
    print("✅ Database startup complete!")


def shutdown_database():
    """Cleanup on shutdown"""
    print("👋 Shutting down database connections...")


# ============================================================================
# STARTUP (for standalone testing)
# ============================================================================

if __name__ == "__main__":
    print("🚀 Initializing Tree of Life AI Database...")
    print("📊 Testing database connection...")
    
    try:
        # Test connection
        if test_connection():
            print("✅ Database connection successful!")
            
            # Create tables
            init_database()
            
            # Create admin user
            create_admin_user()
            
            print("✅ Database setup complete!")
        else:
            print("❌ Database connection failed!")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        raise
