"""
Database models and connection for Tree of Life AI
Uses PostgreSQL with SQLAlchemy ORM
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean, ForeignKey, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from contextlib import contextmanager

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/treeoflife')

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


# ==================== MODELS ====================

class User(Base):
    """User model for authentication and profiles"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation model for chat sessions"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, default="Untitled Conversation")
    preview = Column(String, default="No preview available")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """Message model for individual chat messages"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class HealthProfile(Base):
    """Health profile model for user health information"""
    __tablename__ = "health_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Constitutional Types
    ayurvedic_dosha = Column(String)  # vata, pitta, kapha
    tcm_pattern = Column(String)  # qi deficiency, blood stagnation, etc.
    body_type = Column(String)  # ectomorph, mesomorph, endomorph
    
    # Medical History (stored as JSON)
    current_conditions = Column(JSON, default=list)  # ["anxiety", "insomnia"]
    medications = Column(JSON, default=list)  # [{"name": "Ashwagandha", "dosage": "500mg"}]
    allergies = Column(JSON, default=list)  # ["peanuts", "shellfish"]
    past_diagnoses = Column(JSON, default=list)  # ["depression", "IBS"]
    
    # Lifestyle
    diet_type = Column(String)  # vegetarian, vegan, omnivore
    exercise_frequency = Column(String)  # daily, 3-4x/week, rarely
    sleep_hours = Column(Integer)  # average hours per night
    stress_level = Column(Integer)  # 1-10 scale
    
    # Preferences
    preferred_traditions = Column(JSON, default=list)  # ["ayurveda", "tcm"]
    treatment_philosophy = Column(Text)  # user's approach to health
    health_goals = Column(JSON, default=list)  # ["better sleep", "reduce anxiety"]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="health_profile")


class Symptom(Base):
    """Symptom tracking model"""
    __tablename__ = "symptoms"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    symptom_name = Column(String, nullable=False)
    severity = Column(Integer)  # 1-10 scale
    description = Column(Text)
    duration_hours = Column(Integer)
    triggers = Column(JSON, default=list)
    relieving_factors = Column(JSON, default=list)
    
    logged_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class Treatment(Base):
    """Treatment tracking model"""
    __tablename__ = "treatments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    treatment_name = Column(String, nullable=False)
    treatment_type = Column(String)  # herb, supplement, food, practice
    tradition = Column(String)  # ayurveda, tcm, western, etc.
    dosage = Column(String)
    frequency = Column(String)
    
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    purpose = Column(Text)
    notes = Column(Text)
    effectiveness = Column(Integer)  # 1-5 scale
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== DATABASE FUNCTIONS ====================

def init_database():
    """Initialize database - create all tables"""
    print("🔧 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


def get_db() -> Session:
    """Get database session (FastAPI dependency)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Get database session (context manager)"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def test_connection():
    """Test database connection"""
    try:
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


# ==================== HELPER FUNCTIONS ====================

def create_user(db: Session, email: str, name: str, password_hash: str) -> User:
    """Create a new user"""
    user = User(email=email, name=name, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> User:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


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


def get_conversation(db: Session, conversation_id: str) -> Conversation:
    """Get conversation by ID"""
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_user_conversations(db: Session, user_id: int):
    """Get all conversations for a user"""
    return db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).all()


def add_message(db: Session, conversation_id: str, role: str, content: str) -> Message:
    """Add a message to a conversation"""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    db.add(message)
    
    # Update conversation updated_at
    conversation = get_conversation(db, conversation_id)
    if conversation:
        conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    return message


def delete_conversation(db: Session, conversation_id: str) -> bool:
    """Delete a conversation and all its messages"""
    conversation = get_conversation(db, conversation_id)
    if conversation:
        db.delete(conversation)
        db.commit()
        return True
    return False


def get_or_create_health_profile(db: Session, user_id: int) -> HealthProfile:
    """Get or create health profile for user"""
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    if not profile:
        profile = HealthProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_health_profile(db: Session, user_id: int, **kwargs) -> HealthProfile:
    """Update health profile"""
    profile = get_or_create_health_profile(db, user_id)
    
    for key, value in kwargs.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


# ==================== INITIALIZATION ====================

if __name__ == "__main__":
    print("🚀 Initializing Tree of Life AI Database...")
    test_connection()
    init_database()
    print("✅ Database ready!")
