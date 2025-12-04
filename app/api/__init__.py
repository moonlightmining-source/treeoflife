from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Import and include sub-routers
# from .auth import router as auth_router
# from .chat import router as chat_router
# api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
# api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
