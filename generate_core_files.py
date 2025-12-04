#!/usr/bin/env python3
"""
Generate core Tree of Life AI application files
Based on the AI Medic technical architecture
"""

# File contents as multi-line strings
CONFIG_PY = '''"""
Application Configuration
Manages all environment variables and settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import secrets

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Tree of Life AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Anthropic API
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    
    # Pinecone (optional)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "treeoflifeai"
    
    # OpenAI (for embeddings)
    OPENAI_API_KEY: Optional[str] = None
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Admin User
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "change-this"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get CORS allowed origins as list"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
'''

DATABASE_PY = '''"""
Database Configuration and Session Management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db() -> Session:
    """
    Get database session for dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """
    Get database session for context manager usage
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
'''

MAIN_PY = '''"""
Tree of Life AI - Main FastAPI Application
Integrative Health Intelligence Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    logger.info(f"✅ {settings.APP_NAME} is ready!")
    
    yield
    
    # Shutdown
    logger.info(f"👋 Shutting down {settings.APP_NAME}...")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Tree of Life AI - Integrative Health Intelligence Platform
    
    Combining 10 medical traditions with AI-powered guidance:
    - Western Allopathic Medicine
    - Traditional Chinese Medicine
    - Ayurvedic Medicine
    - Osteopathic Medicine
    - Chiropractic
    - Physical Therapy & Movement Medicine
    - Naturopathic Medicine
    - Homeopathic Medicine
    - Indigenous & Traditional Healing
    - Unani-Tibb Medicine
    
    Plus specialized focus areas:
    - Elder Care & Aging
    - Athletic Performance & Fitness
    - Mental Health & Wellness
    - Women's Health & Fertility
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "api": "/api"
        }
    }

@app.get("/health", tags=["Root"])
async def health_check():
    """Health check endpoint for Railway/monitoring"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

# Debug endpoint
if settings.DEBUG or not settings.is_production:
    @app.get("/debug/env-check", tags=["Debug"])
    async def check_env():
        """Check environment variables (shows last 8 chars only)"""
        def mask_key(key: Optional[str]) -> str:
            if not key:
                return "NOT SET"
            return f"...{key[-8:]}" if len(key) >= 8 else "***"
        
        return {
            "anthropic_key": mask_key(settings.ANTHROPIC_API_KEY),
            "openai_key": mask_key(settings.OPENAI_API_KEY),
            "pinecone_key": mask_key(settings.PINECONE_API_KEY),
            "environment": settings.ENVIRONMENT,
            "allowed_origins": settings.allowed_origins_list
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
'''

# Write files
files = {
    "app/config.py": CONFIG_PY,
    "app/database.py": DATABASE_PY,
    "app/main.py": MAIN_PY
}

for filepath, content in files.items():
    with open(filepath, "w") as f:
        f.write(content)
    print(f"✅ Created {filepath}")

print("\n🎉 Core application files created successfully!")
print("\nYou now have:")
print("  ✅ app/config.py - Configuration & environment variables")
print("  ✅ app/database.py - Database connection & session management")
print("  ✅ app/main.py - FastAPI application with health checks")
print("\nReady to deploy to Railway!")
