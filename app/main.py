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
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("Starting Tree of Life AI backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Tree of Life AI backend...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Integrative Health Intelligence Platform - 10 Medical Traditions",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS configured for origins: {settings.allowed_origins_list}")


# Import and register routers
try:
    from app.api.auth import router as auth_router
    from app.api.chat import router as chat_router
    from app.api.health import router as health_router
    from app.api.tracking import router as tracking_router
    
    # Register all routers with API prefix
    app.include_router(auth_router, prefix=settings.API_V1_STR, tags=["Authentication"])
    app.include_router(chat_router, prefix=settings.API_V1_STR, tags=["Chat"])
    app.include_router(health_router, prefix=settings.API_V1_STR, tags=["Health Profile"])
    app.include_router(tracking_router, prefix=settings.API_V1_STR, tags=["Tracking"])
    
    logger.info("✅ All API routers registered successfully")
    
    # Count registered routes
    route_count = len([route for route in app.routes if hasattr(route, 'methods')])
    logger.info(f"✅ Total registered routes: {route_count}")
    
except Exception as e:
    logger.error(f"❌ Failed to import API routers: {e}", exc_info=True)
    logger.warning("⚠️  API routes not available - check that all router files exist")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health"
    }


# Health check endpoint
@app.get("/health", tags=["Root"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=10000,
        reload=settings.DEBUG
    )
