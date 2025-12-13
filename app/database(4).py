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
    
    # Helper functions
    'check_message_limit',
    'increment_message_count',
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
