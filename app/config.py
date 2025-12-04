"""
Configuration settings for Tree of Life AI
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings - reads from environment variables"""
    
    # Required settings
    DATABASE_URL: str
    REDIS_URL: str
    ANTHROPIC_API_KEY: str
    SECRET_KEY: str
    
    # Optional settings with defaults
    ENVIRONMENT: str = "production"
    ALLOWED_ORIGINS: str = "*"
    
    # Configure to read from environment variables ONLY
    # Don't require .env file (Railway injects vars directly)
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        # Don't specify env_file - read from os.environ
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

# Create settings instance
try:
    settings = Settings()
    print("✅ Settings loaded successfully!")
except Exception as e:
    print(f"❌ Settings failed to load: {e}")
    print(f"Available env vars: {list(os.environ.keys())}")
    raise
