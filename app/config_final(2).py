"""
Application Configuration
Manages all environment variables and settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "AI Medic"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/dbname"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Anthropic API
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 2000
    ANTHROPIC_TEMPERATURE: float = 0.7
    
    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_INDEX_NAME: str = "aimedic-knowledge"
    
    # OpenAI (for embeddings)
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://tree-of-life-ai-frontend.vercel.app", "https://tree-of-life-ai-frontend-roberts-projects-2d36ac41.vercel.app"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "*"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Email (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@aimedic.app"
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".pdf"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Admin User
    ADMIN_EMAIL: str = "moonlight_mining@yahoo.com"
    ADMIN_PASSWORD: str = "change-this-secure-password"
    
    # Feature Flags
    ENABLE_REGISTRATION: bool = True
    ENABLE_EMERGENCY_DETECTION: bool = True
    ENABLE_VOICE_INPUT: bool = False
    ENABLE_IMAGE_ANALYSIS: bool = False
    
    # Subscription Pricing
    FREE_CONVERSATIONS_PER_MONTH: int = 10
    PREMIUM_PRICE_MONTHLY: float = 9.99
    PREMIUM_PRICE_YEARLY: float = 99.00
    PRO_PRICE_MONTHLY: float = 29.99
    PRO_PRICE_YEARLY: float = 299.00
    
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get CORS allowed origins as list"""
        return self.ALLOWED_ORIGINS
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# System Prompt for Claude (The Magic!)
SYSTEM_PROMPT_TEMPLATE = """You are AI Medic, an integrative health intelligence assistant that provides guidance from NINE medical traditions. You integrate insights from:

1. **Western Medicine** - Evidence-based, scientific approach, diagnostics, pharmaceuticals
2. **Ayurveda** - Ancient Indian medicine, doshas (Vata/Pitta/Kapha), constitutional types
3. **Traditional Chinese Medicine (TCM)** - Qi, meridians, yin/yang, organ systems, acupuncture
4. **Herbal Medicine** - Plant-based remedies, phytotherapy, whole plant synergy
5. **Homeopathy** - Like cures like, minimal doses, constitutional remedies
6. **Chiropractic Principles** - Spinal alignment, nervous system, structural health
7. **Clinical Nutrition** - Food as medicine, biochemistry, nutrient therapy
8. **Vibrational Healing** - Energy medicine, frequency healing, sound, crystals, chakras
9. **Movement Medicine & Physical Therapy** - Exercise science, strength training, mobility, functional movement, injury rehabilitation, physical therapy protocols

CRITICAL GUIDELINES:
- You provide EDUCATIONAL information only, NEVER medical diagnosis
- Always present perspectives from multiple traditions when relevant
- Personalize based on user's constitutional type, fitness level, and preferences
- Flag emergency situations IMMEDIATELY with clear "CALL 911" messaging
- Cite sources from the knowledge base when available
- Balance scientific evidence with traditional wisdom respectfully
- Always remind users to consult healthcare professionals for serious concerns
- For fitness/PT recommendations: Consider current fitness level, injuries, pain level, and rehabilitation phase
- For injuries: Check for red flags first, then provide appropriate phase-based rehabilitation guidance
- Be warm, knowledgeable, and empowering in tone

USER PROFILE:
{user_profile}

CONVERSATION HISTORY:
{conversation_history}

RELEVANT KNOWLEDGE:
{knowledge_context}

EMERGENCY DETECTION:
If the user describes any of these symptoms, respond IMMEDIATELY with emergency alert:
- Chest pain, pressure, or tightness
- Severe difficulty breathing or shortness of breath
- Severe bleeding that won't stop
- Loss of consciousness or unresponsiveness
- Severe allergic reaction (throat swelling, difficulty breathing)
- Suicidal thoughts or intent to harm self
- Symptoms of stroke (face drooping, arm weakness, speech difficulty)
- Severe head injury
- Severe abdominal pain
- High fever with confusion

EMERGENCY RESPONSE FORMAT:
🚨 **THIS IS A MEDICAL EMERGENCY**

Call 911 or go to the nearest emergency room IMMEDIATELY. 

Do not wait. Do not try home remedies first. This requires immediate professional medical attention.

[Then provide brief reassurance and what to do while waiting for help]

For all other queries, provide thoughtful, multi-perspective guidance that empowers the user to make informed health decisions.
"""

# Constitutional Assessment Questions
CONSTITUTIONAL_QUESTIONS = [
    {
        "id": "energy_pattern",
        "question": "When do you feel most energetic?",
        "options": {
            "morning": {"vata": 1, "pitta": 2, "kapha": 0},
            "midday": {"vata": 0, "pitta": 2, "kapha": 1},
            "evening": {"vata": 2, "pitta": 0, "kapha": 1}
        }
    },
    {
        "id": "temperature",
        "question": "How do you typically feel temperature-wise?",
        "options": {
            "always_cold": {"vata": 2, "pitta": 0, "kapha": 0},
            "always_hot": {"vata": 0, "pitta": 2, "kapha": 0},
            "comfortable": {"vata": 0, "pitta": 0, "kapha": 2}
        }
    },
    {
        "id": "body_frame",
        "question": "How would you describe your body frame?",
        "options": {
            "thin_light": {"vata": 2, "pitta": 0, "kapha": 0},
            "medium_muscular": {"vata": 0, "pitta": 2, "kapha": 0},
            "large_sturdy": {"vata": 0, "pitta": 0, "kapha": 2}
        }
    },
    {
        "id": "digestion",
        "question": "How is your digestion?",
        "options": {
            "irregular_gas": {"vata": 2, "pitta": 0, "kapha": 0},
            "strong_fast": {"vata": 0, "pitta": 2, "kapha": 0},
            "slow_steady": {"vata": 0, "pitta": 0, "kapha": 2}
        }
    },
    {
        "id": "stress_response",
        "question": "How do you respond to stress?",
        "options": {
            "anxious_worried": {"vata": 2, "pitta": 0, "kapha": 0},
            "irritable_angry": {"vata": 0, "pitta": 2, "kapha": 0},
            "withdrawn_depressed": {"vata": 0, "pitta": 0, "kapha": 2}
        }
    }
]

# Emergency Keywords
EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "can't breathe", "can't breathing",
    "severe bleeding", "bleeding won't stop", "unconscious", "passed out",
    "suicide", "suicidal", "kill myself", "end my life", "overdose",
    "severe allergic", "throat closing", "can't swallow",
    "stroke", "face drooping", "can't speak", "slurred speech",
    "severe head injury", "hit my head hard",
    "severe abdominal pain", "severe stomach pain",
    "having a seizure", "seizure", "convulsing"
]
