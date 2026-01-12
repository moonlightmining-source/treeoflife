"""
Authentication utilities for Tree of Life AI
Extracted from main.py to avoid circular imports
"""
from fastapi import HTTPException, Request
from datetime import datetime, timedelta
import jwt
import bcrypt
import os

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {'user_id': str(user_id), 'exp': datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(request: Request) -> str:
    """Extract user_id from JWT token in Authorization header"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth_header.split(' ')[1]
    return verify_token(token)

