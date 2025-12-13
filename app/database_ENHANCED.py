"""
Enhanced Database Models for AI Medic
Includes: Subscriptions, Family Members, Pro Features
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from contextlib import contextmanager
import os

Base = declarative_base()

# ============================================================================
# USER MODELS
# ============================================================================

class User(Base):
    """User accounts with authentication"""
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Subscription info
    subscription_tier = Column(String, default='free')  # free, premium, pro
    subscription_status = Column(String, default='active')  # active, cancelled, expired
    subscription_expires_at = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    
    # Usage tracking
    messages_this_month = Column(Integer, default=0)
    messages_reset_date = Column(DateTime, default=lambda: datetime.utcnow().replace(day=1))
    
    # Relationships
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user")
    symptoms = relationship("Symptom", back_populates="user")
    treatments = relationship("Treatment", back_populates="user")
    family_members = relationship("FamilyMember", back_populates="user")
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'subscription_tier': self.subscription_tier,
            'subscription_status': self.subscription_status,
            'created_at': self.created_at.isoformat()
        }

class HealthProfile(Base):
    """User health profile with constitutional assessment"""
    __tablename__ = 'health_profiles'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, unique=True)
    
    # Constitutional types
    ayurvedic_dosha = Column(String)  # vata, pitta, kapha
    tcm_pattern = Column(String)      # qi deficiency, blood stagnation, etc.
    body_type = Column(String)        # ectomorph, mesomorph, endomorph
    
    # Medical history (JSON for flexibility)
    current_conditions = Column(JSON, default=list)
    medications = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    family_history = Column(JSON, default=dict)
    
    # Lifestyle
    diet_type = Column(String)
    exercise_frequency = Column(String)
    sleep_hours = Column(Float)
    stress_level = Column(Integer)  # 1-10
    
    # Preferences
    preferred_traditions = Column(JSON, default=list)
    treatment_philosophy = Column(Text)
    health_goals = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="health_profile")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ayurvedic_dosha': self.ayurvedic_dosha,
            'tcm_pattern': self.tcm_pattern,
            'body_type': self.body_type,
            'current_conditions': self.current_conditions or [],
            'medications': self.medications or [],
            'allergies': self.allergies or [],
            'diet_type': self.diet_type,
            'exercise_frequency': self.exercise_frequency,
            'sleep_hours': self.sleep_hours,
            'stress_level': self.stress_level,
            'preferred_traditions': self.preferred_traditions or [],
            'health_goals': self.health_goals or []
        }

# ============================================================================
# FAMILY MEMBER MODELS
# ============================================================================

class FamilyMember(Base):
    """Family member profiles for Premium/Pro users"""
    __tablename__ = 'family_members'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    
    name = Column(String, nullable=False)
    member_relationship = Column(String)  # self, spouse, child, parent, etc.
    date_of_birth = Column(String)
    gender = Column(String, nullable=True)
    
    # Each family member has their own health profile
    health_profile_data = Column(JSON, default=dict)
    
    is_active = Column(Boolean, default=False)  # Currently active profile
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="family_members")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'relationship': self.member_relationship,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'is_active': self.is_active,
            'health_profile': self.health_profile_data or {}
        }

# ============================================================================
# CONVERSATION MODELS
# ============================================================================

class Conversation(Base):
    """Chat conversations"""
    __tablename__ = 'conversations'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    family_member_id = Column(String, nullable=True)  # If chat is for family member
    
    title = Column(String)
    preview = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'preview': self.preview,
            'family_member_id': self.family_member_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Message(Base):
    """Individual chat messages"""
    __tablename__ = 'messages'
    
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=False)
    
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }

# ============================================================================
# HEALTH TRACKING MODELS
# ============================================================================

class Symptom(Base):
    """Symptom tracking"""
    __tablename__ = 'symptoms'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    family_member_id = Column(String, nullable=True)
    
    symptom_name = Column(String, nullable=False)
    severity = Column(Integer)  # 1-10
    description = Column(Text)
    triggers = Column(JSON, default=list)
    logged_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="symptoms")
    
    def to_dict(self):
        return {
            'id': self.id,
            'symptom_name': self.symptom_name,
            'severity': self.severity,
            'description': self.description,
            'triggers': self.triggers or [],
            'logged_at': self.logged_at.isoformat()
        }

class Treatment(Base):
    """Treatment tracking"""
    __tablename__ = 'treatments'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    family_member_id = Column(String, nullable=True)
    
    treatment_name = Column(String, nullable=False)
    treatment_type = Column(String)  # herb, supplement, food, exercise, etc.
    tradition = Column(String)       # ayurveda, tcm, western, etc.
    dosage = Column(String)
    frequency = Column(String)
    effectiveness = Column(Integer)  # 1-5 rating
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="treatments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'treatment_name': self.treatment_name,
            'treatment_type': self.treatment_type,
            'tradition': self.tradition,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'effectiveness': self.effectiveness,
            'is_active': self.is_active,
            'started_at': self.started_at.isoformat()
        }

# ============================================================================
# PRO FEATURES MODELS
# ============================================================================

class CustomProtocol(Base):
    """Custom protocols created by Pro users"""
    __tablename__ = 'custom_protocols'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    traditions = Column(JSON, default=list)  # Which traditions used
    
    # Protocol content
    steps = Column(JSON, default=list)
    duration_weeks = Column(Integer)
    
    # Tags and categorization
    tags = Column(JSON, default=list)
    condition = Column(String)
    
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'traditions': self.traditions or [],
            'steps': self.steps or [],
            'duration_weeks': self.duration_weeks,
            'tags': self.tags or [],
            'condition': self.condition,
            'created_at': self.created_at.isoformat()
        }

class ClientRecord(Base):
    """Client records for Pro practitioners"""
    __tablename__ = 'client_records'
    
    id = Column(String, primary_key=True)
    practitioner_id = Column(String, ForeignKey('users.id'), nullable=False)
    
    client_name = Column(String, nullable=False)
    client_email = Column(String)
    constitution = Column(String)
    
    active_protocol_id = Column(String, nullable=True)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_session = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'client_name': self.client_name,
            'client_email': self.client_email,
            'constitution': self.constitution,
            'active_protocol_id': self.active_protocol_id,
            'last_session': self.last_session.isoformat() if self.last_session else None
        }

# ============================================================================
# DATABASE CONNECTION & UTILITIES
# ============================================================================

# Database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/aimedic')

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize database - create all tables"""
    try:
        # Test connection first
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        
        # Create all tables
        Base.metadata.create_all(engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False

def test_connection():
    """Test database connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

@contextmanager
def get_db_context():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_db():
    """Get database session (for FastAPI dependency injection)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_by_email(db, email: str):
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db, user_id: str):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db, user_id: str, email: str, name: str, password_hash: str):
    """Create new user"""
    user = User(
        id=user_id,
        email=email,
        name=name,
        password_hash=password_hash
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_conversations(db, user_id: str):
    """Get all conversations for a user"""
    return db.query(Conversation)\
        .filter(Conversation.user_id == user_id)\
        .order_by(Conversation.updated_at.desc())\
        .all()

def get_conversation(db, conversation_id: str, user_id: str):
    """Get specific conversation"""
    return db.query(Conversation)\
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)\
        .first()

def create_conversation(db, conversation_id: str, user_id: str, title: str, preview: str = ""):
    """Create new conversation"""
    conv = Conversation(
        id=conversation_id,
        user_id=user_id,
        title=title,
        preview=preview
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

def add_message(db, message_id: str, conversation_id: str, role: str, content: str):
    """Add message to conversation"""
    message = Message(
        id=message_id,
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    db.add(message)
    db.commit()
    return message

def get_messages(db, conversation_id: str):
    """Get all messages in a conversation"""
    return db.query(Message)\
        .filter(Message.conversation_id == conversation_id)\
        .order_by(Message.created_at.asc())\
        .all()

def delete_conversation(db, conversation_id: str, user_id: str):
    """Delete a conversation and all its messages"""
    conv = get_conversation(db, conversation_id, user_id)
    if conv:
        db.delete(conv)
        db.commit()
        return True
    return False

def get_health_profile(db, user_id: str):
    """Get user's health profile"""
    return db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()

def create_health_profile(db, profile_id: str, user_id: str, **kwargs):
    """Create health profile"""
    profile = HealthProfile(id=profile_id, user_id=user_id, **kwargs)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

def update_health_profile(db, user_id: str, **kwargs):
    """Update health profile"""
    profile = get_health_profile(db, user_id)
    if profile:
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
    return profile

# Subscription helpers
def check_message_limit(db, user_id: str) -> tuple[bool, int]:
    """Check if user has reached message limit"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False, 0
    
    # Reset counter if new month
    if user.messages_reset_date < datetime.utcnow().replace(day=1):
        user.messages_this_month = 0
        user.messages_reset_date = datetime.utcnow().replace(day=1)
        db.commit()
    
    # Free tier: 10 messages/month
    if user.subscription_tier == 'free':
        if user.messages_this_month >= 10:
            return False, 10
        return True, user.messages_this_month
    
    # Premium/Pro: unlimited
    return True, user.messages_this_month

def increment_message_count(db, user_id: str):
    """Increment user's message count"""
    user = get_user_by_id(db, user_id)
    if user:
        user.messages_this_month += 1
        db.commit()

# Family member helpers
def get_family_members(db, user_id: str):
    """Get all family members for a user"""
    return db.query(FamilyMember)\
        .filter(FamilyMember.user_id == user_id)\
        .all()

def get_active_family_member(db, user_id: str):
    """Get currently active family member"""
    return db.query(FamilyMember)\
        .filter(FamilyMember.user_id == user_id, FamilyMember.is_active == True)\
        .first()

def create_family_member(db, member_id: str, user_id: str, **kwargs):
    """Create family member"""
    member = FamilyMember(id=member_id, user_id=user_id, **kwargs)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def switch_active_profile(db, user_id: str, member_id: str):
    """Switch active family profile"""
    # Deactivate all
    db.query(FamilyMember)\
        .filter(FamilyMember.user_id == user_id)\
        .update({'is_active': False})
    
    # Activate selected
    member = db.query(FamilyMember)\
        .filter(FamilyMember.id == member_id, FamilyMember.user_id == user_id)\
        .first()
    
    if member:
        member.is_active = True
        db.commit()
        return member
    return None

print("✅ Enhanced database models loaded successfully!")
