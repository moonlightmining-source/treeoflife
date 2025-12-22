"""
AI Medic - Main FastAPI Application
Integrative Health Intelligence Platform
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time

from app.config import settings
from app.database import init_db, create_admin_user
from app.api import (
    auth_router,
    chat_router,
    health_router,
    tracking_router,
    fitness_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting AI Medic backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Create admin user
    try:
        create_admin_user()
        logger.info("✅ Admin user verified")
    except Exception as e:
        logger.warning(f"⚠️  Admin user check failed: {e}")
    
    logger.info("✅ AI Medic backend is ready!")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down AI Medic backend...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    AI Medic - Integrative Health Intelligence Platform
    
    A comprehensive health guidance platform integrating 9 medical traditions:
    - Western Medicine
    - Ayurveda  
    - Traditional Chinese Medicine
    - Herbal Medicine
    - Homeopathy
    - Chiropractic
    - Clinical Nutrition
    - Vibrational Healing
    - Movement Medicine & Physical Therapy
    
    Powered by Anthropic Claude AI with RAG (Retrieval-Augmented Generation).
    """,
    docs_url="/docs" if settings.DEBUG else None,  # Disable in production
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)


# ========== MIDDLEWARE ==========

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS.split(","),
    allow_headers=settings.CORS_ALLOW_HEADERS.split(","),
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# ========== EXCEPTION HANDLERS ==========

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred" if settings.is_production else str(exc)
            }
        }
    )


# ========== ROUTES ==========

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "endpoints": {
            "auth": "/api/auth",
            "chat": "/api/chat",
            "health": "/api/health",
            "tracking": "/api/tracking",
            "fitness": "/api/fitness"
        }
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Register API routers
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(tracking_router, prefix="/api")
app.include_router(fitness_router, prefix="/api")


# ========== UTILITY ENDPOINTS (Development only) ==========

if settings.DEBUG:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Debug endpoint to view configuration (dev only)"""
        return {
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "anthropic_model": settings.ANTHROPIC_MODEL,
            "free_conversations_limit": settings.FREE_CONVERSATIONS_PER_MONTH,
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
