"""
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
