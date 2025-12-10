from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import re

# Import your routers
# from app.api import auth, chat, health, tracking

app = FastAPI(
    title="Tree of Life AI API",
    description="Integrative Health Intelligence Platform",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed origins list
ALLOWED_ORIGINS = [
    # Production domains
    "https://treeoflifeai.com",
    "https://www.treeoflifeai.com",
    # Local development
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

# Pattern for Vercel preview domains
VERCEL_PATTERN = re.compile(r"https://.*\.vercel\.app$")

# Custom CORS middleware that allows Vercel preview domains
@app.middleware("http")
async def cors_middleware(request, call_next):
    origin = request.headers.get("origin")
    
    # Check if origin is allowed
    is_allowed = False
    if origin:
        if origin in ALLOWED_ORIGINS:
            is_allowed = True
        elif VERCEL_PATTERN.match(origin):
            is_allowed = True
    
    response = await call_next(request)
    
    if is_allowed and origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# Also add standard CORS middleware for OPTIONS preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel domains
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "message": "Tree of Life AI API",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "message": "Backend is awake and running"
    }

# Include your API routers here
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
# app.include_router(health.router, prefix="/api/health", tags=["health"])
# app.include_router(tracking.router, prefix="/api/tracking", tags=["tracking"])

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Tree of Life AI API starting up...")
    logger.info("CORS enabled for:")
    for origin in ALLOWED_ORIGINS:
        logger.info(f"  - {origin}")
    logger.info("  - All *.vercel.app domains")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Tree of Life AI API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
