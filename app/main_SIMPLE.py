"""
Tree of Life AI - Minimal Working Backend
Super simple version with auth built-in
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

app = FastAPI(title="Tree of Life AI API")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory user storage (replace with database later)
users = {}

# JWT config
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

# CORS - Allow your domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://treeoflifeai.com",
        "https://www.treeoflifeai.com",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    terms_accepted: bool

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Helper functions
def create_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

# Routes
@app.get("/")
def root():
    return {
        "message": "Tree of Life AI API",
        "status": "online",
        "version": "1.0.0",
        "auth_endpoints": ["/api/auth/login", "/api/auth/register"]
    }

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/auth/register")
def register(user: UserRegister):
    print(f"Register attempt: {user.email}")
    
    if not user.terms_accepted:
        raise HTTPException(status_code=400, detail="Must accept terms")
    
    if user.email in users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be 8+ characters")
    
    # Save user
    users[user.email] = {
        "email": user.email,
        "password": pwd_context.hash(user.password),
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
    
    print(f"User registered: {user.email}")
    
    return {
        "success": True,
        "token": create_token(user.email),
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
    }

@app.post("/api/auth/login")
def login(credentials: UserLogin):
    print(f"Login attempt: {credentials.email}")
    
    user = users.get(credentials.email)
    if not user:
        print(f"User not found: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not pwd_context.verify(credentials.password, user["password"]):
        print(f"Invalid password for: {credentials.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    print(f"Login successful: {credentials.email}")
    
    return {
        "success": True,
        "token": create_token(credentials.email),
        "user": {
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"]
        }
    }

@app.get("/api/auth/test")
def test_auth():
    return {
        "message": "Auth endpoint is working!",
        "registered_users": len(users)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
