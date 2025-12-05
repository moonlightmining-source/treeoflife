"""
Configuration settings for Tree of Life AI
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings - reads from environment variables"""
    
    # REQUIRED settings
    DATABASE_URL: str
    ANTHROPIC_API_KEY: str
    SECRET_KEY: str
    
    # OPTIONAL - Redis (for caching/sessions)
    REDIS_URL: Optional[str] = None
    
    # OPTIONAL settings with defaults
    ENVIRONMENT: str = "production"
    ALLOWED_ORIGINS: str = "*"
    
    # OPTIONAL - Pinecone (for knowledge base)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = "us-west1-gcp"
    PINECONE_INDEX_NAME: Optional[str] = "health-knowledge"
    
    # OPTIONAL - OpenAI (for embeddings)
    OPENAI_API_KEY: Optional[str] = None
    
    # OPTIONAL - Admin user
    ADMIN_EMAIL: Optional[str] = "admin@treeoflife.ai"
    ADMIN_PASSWORD: Optional[str] = None
    
    # Configure to read from environment variables
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
    )
    
    @property
    def allowed_origins_list(self) -> list[str]:
        """Convert ALLOWED_ORIGINS string to list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# Debug: Print what's in the environment
print("🔍 Checking environment variables...")
print(f"DATABASE_URL present: {'DATABASE_URL' in os.environ}")
print(f"REDIS_URL present: {'REDIS_URL' in os.environ}")
print(f"ANTHROPIC_API_KEY present: {'ANTHROPIC_API_KEY' in os.environ}")
print(f"SECRET_KEY present: {'SECRET_KEY' in os.environ}")
print(f"PINECONE_API_KEY present: {'PINECONE_API_KEY' in os.environ}")
print(f"OPENAI_API_KEY present: {'OPENAI_API_KEY' in os.environ}")

# Create settings instance
try:
    settings = Settings()
    print("✅ Settings loaded successfully!")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    print(f"🔌 Pinecone enabled: {settings.PINECONE_API_KEY is not None}")
    print(f"🔌 OpenAI enabled: {settings.OPENAI_API_KEY is not None}")
except Exception as e:
    print(f"❌ Settings failed to load: {e}")
    print(f"Available env vars: {list(os.environ.keys())}")
    raise
