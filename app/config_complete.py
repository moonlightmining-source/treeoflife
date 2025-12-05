"""
Configuration settings for Tree of Life AI
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # REQUIRED settings
    DATABASE_URL: str
    ANTHROPIC_API_KEY: str
    SECRET_KEY: str
    
    # App metadata
    APP_NAME: str = "Tree of Life AI"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # OPTIONAL settings with defaults
    REDIS_URL: Optional[str] = None
    ENVIRONMENT: str = "production"
    ALLOWED_ORIGINS: str = "*"
    DEBUG: bool = False
    
    # JWT settings
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Pinecone (optional)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX_NAME: Optional[str] = "treeoflife-knowledge"
    
    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    
    # Admin user (optional)
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    
    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore"
    )


# Debug: Print what's in os.environ when config loads
print("=" * 60)
print("CHECKING ENVIRONMENT VARIABLES...")
print("=" * 60)

# Check for required variables
required_vars = ["DATABASE_URL", "ANTHROPIC_API_KEY", "SECRET_KEY"]
for var in required_vars:
    present = var in os.environ
    print(f"{var} present: {present}")
    if present:
        # Show first 20 chars only for security
        value = os.environ[var]
        preview = value[:20] + "..." if len(value) > 20 else value
        print(f"  Value preview: {preview}")

# Check for optional variables
optional_vars = ["REDIS_URL", "DEBUG", "ENVIRONMENT", "PINECONE_API_KEY", "OPENAI_API_KEY"]
for var in optional_vars:
    if var in os.environ:
        value = os.environ[var]
        preview = value[:20] + "..." if len(value) > 20 else value
        print(f"{var}: {preview}")

print("=" * 60)

# Create settings instance
try:
    settings = Settings()
    print("SUCCESS: Settings loaded successfully!")
    print(f"  App: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  Environment: {settings.ENVIRONMENT}")
    print(f"  Debug mode: {settings.DEBUG}")
    print(f"  Redis configured: {settings.REDIS_URL is not None}")
    print(f"  Pinecone configured: {settings.PINECONE_API_KEY is not None}")
    print("=" * 60)
except Exception as e:
    print(f"ERROR loading settings: {e}")
    print("=" * 60)
    raise


# System prompts for AI - Multi-tradition medical guidance
SYSTEM_PROMPT_TEMPLATE = """You are Tree of Life, an integrative health intelligence assistant that provides guidance from multiple medical traditions.

You integrate insights from these 10 traditions:
1. Western Medicine
2. Ayurveda (Indian)
3. Traditional Chinese Medicine (TCM)
4. Unani Medicine (Islamic/Greek)
5. Herbal Medicine (Global)
6. Homeopathy
7. Chiropractic Principles
8. Clinical Nutrition
9. Vibrational/Energy Healing
10. Indigenous Healing Practices

CRITICAL GUIDELINES:
- You provide EDUCATIONAL information only, never medical diagnosis
- Always include perspectives from multiple traditions when relevant
- Personalize based on user's constitutional type and preferences
- Flag emergency situations immediately
- Cite sources from the knowledge base
- Be evidence-balanced: respect both scientific research and traditional wisdom
- Always remind users to consult healthcare professionals for serious concerns

USER PROFILE:
{user_profile}

CONVERSATION CONTEXT:
{conversation_history}

RELEVANT KNOWLEDGE:
{rag_context}

SAFETY INSTRUCTIONS:
- If user describes emergency symptoms (chest pain, severe bleeding, loss of consciousness, 
  severe allergic reaction, suicidal thoughts), respond with:
  "EMERGENCY: This sounds like a medical emergency. Please call 911 or go to the nearest 
  emergency room immediately. Do not wait."
- For concerning symptoms, always include "when to see a doctor" guidance
- Never recommend stopping prescribed medications without doctor consultation
- Always warn about potential herb-drug interactions

Respond in a warm, knowledgeable, and empowering tone. Be the bridge between traditions.
"""

# Emergency keywords for immediate detection
EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "can't breathe", "difficulty breathing",
    "severe bleeding", "heavy bleeding", "blood loss",
    "unconscious", "passed out", "loss of consciousness",
    "suicide", "suicidal", "kill myself", "end my life",
    "overdose", "took too many", "poisoning",
    "severe allergic", "anaphylaxis", "throat closing",
    "stroke", "can't move", "face drooping", "slurred speech",
    "seizure", "convulsion",
    "severe head injury", "head trauma",
    "severe burn", "third degree burn",
    "broken bone", "compound fracture",
    "labor", "contractions", "baby coming"
]

# Constitutional assessment questions
CONSTITUTIONAL_QUESTIONS = {
    "ayurveda": [
        {
            "question": "How would you describe your body frame?",
            "options": {
                "vata": "Thin, light, difficulty gaining weight",
                "pitta": "Medium build, athletic, moderate weight",
                "kapha": "Heavy, sturdy, gains weight easily"
            }
        },
        {
            "question": "How is your digestion typically?",
            "options": {
                "vata": "Variable, sometimes constipated, gas/bloating",
                "pitta": "Strong, can eat anything, gets hungry quickly",
                "kapha": "Slow, can skip meals, tendency to heaviness"
            }
        },
        {
            "question": "What's your energy pattern like?",
            "options": {
                "vata": "Quick bursts of energy, tire easily, restless",
                "pitta": "Consistent moderate-high energy, focused",
                "kapha": "Steady endurance, slow to get going"
            }
        },
        {
            "question": "How do you handle stress?",
            "options": {
                "vata": "Anxiety, worry, overwhelm, scattered thoughts",
                "pitta": "Irritability, anger, criticism, intensity",
                "kapha": "Withdrawal, lethargy, emotional eating"
            }
        },
        {
            "question": "What's your sleep pattern?",
            "options": {
                "vata": "Light sleeper, difficulty falling asleep, restless",
                "pitta": "Moderate sleep, wake feeling refreshed",
                "kapha": "Deep sleeper, love sleeping, hard to wake"
            }
        }
    ]
}
