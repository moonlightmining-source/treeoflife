"""
Tree of Life AI - Main Application
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    """
    Startup and shutdown events
    """
    # Startup
    logger.info("Starting Tree of Life AI backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Tree of Life AI backend...")


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
    lifespan=lifespan,
    docs_url="/docs",  # ALWAYS ENABLED
    redoc_url="/redoc",  # ALWAYS ENABLED
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
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
            "api": settings.API_V1_STR,
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway/monitoring"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Import and include API routers
try:
    from app.api.auth import router as auth_router
    from app.api.chat import router as chat_router
    from app.api.health import router as health_router
    from app.api.tracking import router as tracking_router
    
    # Register routers with prefix
    app.include_router(auth_router, prefix=settings.API_V1_STR, tags=["Authentication"])
    app.include_router(chat_router, prefix=settings.API_V1_STR, tags=["Chat"])
    app.include_router(health_router, prefix=settings.API_V1_STR, tags=["Health Profile"])
    app.include_router(tracking_router, prefix=settings.API_V1_STR, tags=["Tracking"])
    
    logger.info("All API routers registered successfully")
    logger.info(f"Registered routes: {len(app.routes)}")
    
except ImportError as e:
    logger.error(f"Failed to import API routers: {e}")
    logger.warning("API routes not available - check that all router files exist")
    # Print detailed error
    import traceback
    logger.error(traceback.format_exc())


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "details": str(exc) if settings.DEBUG else None
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug" if settings.DEBUG else "info"
    )
