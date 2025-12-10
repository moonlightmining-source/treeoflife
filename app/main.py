"""
Tree of Life AI - Main FastAPI Application
Complete working version with auth endpoints
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

app = FastAPI(
    title="Tree of Life AI API",
    description="Integrative Health Intelligence Platform",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS Configuration - CRITICAL FOR FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Production
        "https://treeoflifeai.com",
        "https://www.treeoflifeai.com",
        # Vercel deployments
        "https://tree-of-life-ai-frontend-git-main-roberts-projects-2d36ac41.vercel.app",
        "https://tree-of-life-ai-frontend.vercel.app",
        # Local development
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel preview domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import auth router
# Put auth_router.py in app/api/auth.py
try:
    from app.api.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    logger.info("✅ Auth router loaded")
except ImportError as e:
    logger.warning(f"⚠️  Auth router not found: {e}")
    logger.warning("Creating inline auth routes...")
    
    # Inline auth routes if separate file doesn't exist
    from fastapi import APIRouter, HTTPException, status
    from pydantic import BaseModel, EmailStr
    from passlib.context import CryptContext
    from datetime import datetime, timedelta
    import jwt
    
    auth_router = APIRouter()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    users_db = {}  # In-memory storage
    
    SECRET_KEY = "change-this-secret-key-in-production"
    ALGORITHM = "HS256"
    
    class UserRegister(BaseModel):
        email: EmailStr
        password: str
        first_name: str
        last_name: str
        terms_accepted: bool
    
    class UserLogin(BaseModel):
        email: EmailStr
        password: str
    
    def create_token(email: str) -> str:
        expire = datetime.utcnow() + timedelta(days=7)
        return jwt.encode({"sub": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    
    @auth_router.post("/register")
    async def register(user: UserRegister):
        if not user.terms_accepted:
            raise HTTPException(status_code=400, detail="Must accept terms")
        if user.email in users_db:
            raise HTTPException(status_code=400, detail="Email already registered")
        if len(user.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be 8+ characters")
        
        users_db[user.email] = {
            "email": user.email,
            "hashed_password": pwd_context.hash(user.password),
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        
        return {
            "success": True,
            "token": create_token(user.email),
            "user": {"email": user.email, "first_name": user.first_name, "last_name": user.last_name}
        }
    
    @auth_router.post("/login")
    async def login(creds: UserLogin):
        user = users_db.get(creds.email)
        if not user or not pwd_context.verify(creds.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return {
            "success": True,
            "token": create_token(creds.email),
            "user": {"email": user["email"], "first_name": user["first_name"], "last_name": user["last_name"]}
        }
    
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    logger.info("✅ Inline auth routes created")

# Root endpoint
@app.get("/")
async def root():
    """API information"""
    return {
        "message": "Tree of Life AI API",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth/login, /api/auth/register",
            "health": "/health",
            "docs": "/docs"
        }
    }

# Health check
@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "message": "Backend is awake",
        "timestamp": datetime.utcnow().isoformat()
    }

# Startup
@app.on_event("startup")
async def startup():
    logger.info("🌳 Tree of Life AI API starting...")
    logger.info("📍 CORS enabled for treeoflifeai.com and Vercel")
    logger.info("🔑 Auth endpoints ready at /api/auth/*")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
