"""
Database Configuration and Connection
"""
import logging
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """
    Database dependency for FastAPI routes
    Yields a database session and ensures it's closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions (for scripts/background tasks)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    """
    # Import all models to ensure they're registered with Base
    from app.models import (
        user,
        health_profile,
        conversation,
        message,
        symptom,
        treatment,
        knowledge
    )
    
    logger.info("Creating database tables...")
    
    # Check if we should reset the database (DEVELOPMENT ONLY!)
    if os.getenv("RESET_DATABASE") == "true":
        logger.warning("🚨 RESET_DATABASE=true - DROPPING ALL TABLES!")
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ All tables dropped")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def create_admin_user():
    """
    Create admin user if not exists
    """
    from app.models.user import User
    from app.utils.security import get_password_hash
    
    with get_db_context() as db:
        # Check if admin exists
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        
        if not admin:
            logger.info("Creating admin user...")
            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                first_name="Admin",
                last_name="User",
                date_of_birth="1980-01-01",
                sex="other",
                location="00000",
                subscription_tier="pro",
                subscription_status="active",
                is_active=True,
                email_verified=True
            )
            db.add(admin)
            db.commit()
            logger.info(f"✅ Admin user created: {settings.ADMIN_EMAIL}")
        else:
            logger.info("Admin user already exists")
