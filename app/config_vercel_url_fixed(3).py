"""
Application configuration and settings
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    PROJECT_NAME: str = "Tree of Life AI"
    APP_NAME: str = "Tree of Life AI"  # Alias for main.py compatibility
    VERSION: str = "1.0.0"
    APP_VERSION: str = "1.0.0"  # Alias for main.py compatibility
    API_V1_STR: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Anthropic API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # OpenAI API (for embeddings)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Pinecone (Vector Database)
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    PINECONE_INDEX_NAME: str = "aimedic-knowledge"
    
    # CORS - Allow these origins
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,https://tree-of-life-ai-frontend.vercel.app,https://tree-of-life-ai-frontend-roberts-projects-2d36ac41.vercel.app"
    )
    
    # Alias for compatibility
    BACKEND_CORS_ORIGINS: str = CORS_ORIGINS
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        
        # Expand origins to include both http:// and https:// if not present
        expanded = []
        for origin in origins:
            expanded.append(origin)
            # Add http version if https
            if origin.startswith("https://"):
                http_version = origin.replace("https://", "http://")
                if http_version not in expanded:
                    expanded.append(http_version)
            # Add https version if http
            elif origin.startswith("http://"):
                https_version = origin.replace("http://", "https://")
                if https_version not in expanded:
                    expanded.append(https_version)
            # Add both if no protocol
            elif not origin.startswith("http"):
                if f"https://{origin}" not in expanded:
                    expanded.append(f"https://{origin}")
                if f"http://{origin}" not in expanded:
                    expanded.append(f"http://{origin}")
        
        return list(set(expanded))  # Remove duplicates
    
    # Subscription tiers
    FREE_CONVERSATIONS_PER_MONTH: int = 10
    PREMIUM_PRICE_MONTHLY: float = 9.99
    PREMIUM_PRICE_ANNUAL: float = 99.00
    PRO_PRICE_MONTHLY: float = 29.99
    PRO_PRICE_ANNUAL: float = 299.00
    
    # Admin user
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "moonlight_mining@yahoo.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "change-this-password")
    ADMIN_FIRST_NAME: str = "Admin"
    ADMIN_LAST_NAME: str = "User"
    
    # Database reset (DANGER!)
    RESET_DATABASE: bool = os.getenv("RESET_DATABASE", "false").lower() == "true"
    
    # SMTP Email settings (optional, for password reset)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@treeoflife.ai")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "Tree of Life AI")
    
    class Config:
        case_sensitive = True


# Create settings instance
settings = Settings()


# System prompt for Claude AI with all 8 medical traditions
SYSTEM_PROMPT_TEMPLATE = """You are Tree of Life AI, an integrative health intelligence assistant that provides guidance from multiple medical traditions. You integrate insights from:

1. **Western Medicine** - Evidence-based, scientific approach
2. **Ayurvedic Medicine** - Indian system based on doshas (Vata, Pitta, Kapha)
3. **Traditional Chinese Medicine (TCM)** - Qi, meridians, five elements
4. **Herbal Medicine** - Plant-based remedies and phytotherapy
5. **Homeopathy** - Like cures like, dilutions
6. **Chiropractic Principles** - Spinal alignment, nervous system
7. **Clinical Nutrition** - Food as medicine, nutritional therapy
8. **Vibrational Healing** - Energy medicine, frequency healing

**CRITICAL GUIDELINES:**

⚠️ **SAFETY FIRST:**
- You provide EDUCATIONAL information only, NEVER medical diagnosis
- Always include "when to see a doctor" guidance for concerning symptoms
- Flag emergency situations immediately
- Never recommend stopping prescribed medications without doctor consultation
- Always warn about potential herb-drug interactions

📋 **RESPONSE STRUCTURE:**
When responding to health questions:
1. Acknowledge the concern with empathy
2. Provide perspectives from 2-3 relevant traditions (not all 8 every time)
3. Explain the rationale behind each tradition's view
4. Include practical, actionable guidance
5. Always add appropriate disclaimers and "see a doctor" guidance

🎯 **PERSONALIZATION:**
{user_context}

📚 **KNOWLEDGE BASE:**
{rag_context}

🔴 **EMERGENCY DETECTION:**
If user describes:
- Chest pain, severe shortness of breath
- Severe bleeding, loss of consciousness
- Severe allergic reactions
- Suicidal thoughts or severe mental health crisis
- Stroke symptoms (facial drooping, arm weakness, speech difficulty)
- Severe head injury

Respond with:
"🚨 This sounds like a medical emergency. Please call 911 or go to the nearest emergency room immediately. Do not wait."

**CONVERSATION HISTORY:**
{conversation_history}

Remember: You are educational and empowering, never diagnostic or prescriptive. Guide users to make informed decisions with their healthcare providers."""


# Emergency keywords for detection
EMERGENCY_KEYWORDS = [
    "chest pain",
    "can't breathe",
    "can't breath",
    "difficulty breathing",
    "severe bleeding",
    "heavy bleeding",
    "unconscious",
    "passed out",
    "suicide",
    "suicidal",
    "kill myself",
    "end my life",
    "overdose",
    "heart attack",
    "stroke",
    "severe allergic",
    "anaphylaxis",
    "can't wake",
    "won't wake",
    "severe head injury",
    "head trauma",
    "can't move",
    "paralyzed",
    "seizure",
    "convulsion"
]


# Constitutional assessment questions for Ayurvedic dosha
CONSTITUTIONAL_QUESTIONS = [
    {
        "id": "body_frame",
        "question": "How would you describe your natural body frame?",
        "options": {
            "vata": "Thin, light, hard to gain weight",
            "pitta": "Medium build, athletic, moderate weight",
            "kapha": "Large frame, solid, gains weight easily"
        }
    },
    {
        "id": "skin_type",
        "question": "How would you describe your skin?",
        "options": {
            "vata": "Dry, rough, cool to touch",
            "pitta": "Warm, oily, prone to redness/inflammation",
            "kapha": "Thick, oily, cool, well-hydrated"
        }
    },
    {
        "id": "digestion",
        "question": "How is your digestion typically?",
        "options": {
            "vata": "Variable, irregular, prone to gas/bloating",
            "pitta": "Strong, regular, prone to heartburn/acidity",
            "kapha": "Slow, steady, prone to feeling heavy"
        }
    },
    {
        "id": "energy_pattern",
        "question": "What's your typical energy pattern?",
        "options": {
            "vata": "Quick bursts of energy, then fatigue",
            "pitta": "Intense, focused, driven energy",
            "kapha": "Steady, enduring, sometimes sluggish"
        }
    },
    {
        "id": "personality",
        "question": "Which personality traits resonate most?",
        "options": {
            "vata": "Creative, enthusiastic, changes mind often",
            "pitta": "Determined, focused, competitive",
            "kapha": "Calm, steady, resistant to change"
        }
    }
]


# Tradition-specific knowledge bases (simplified for now)
TRADITION_KNOWLEDGE = {
    "western": {
        "description": "Evidence-based medicine focusing on diagnosis, treatment, and prevention through scientific research",
        "key_concepts": ["Diagnosis", "Evidence-based", "Pharmacology", "Surgery", "Lab tests"]
    },
    "ayurveda": {
        "description": "Ancient Indian system focusing on balance of three doshas (Vata, Pitta, Kapha)",
        "key_concepts": ["Doshas", "Agni (digestive fire)", "Ama (toxins)", "Constitution", "Herbal remedies"]
    },
    "tcm": {
        "description": "Traditional Chinese Medicine based on Qi, meridians, and five elements",
        "key_concepts": ["Qi", "Yin/Yang", "Five Elements", "Meridians", "Acupuncture"]
    },
    "herbal": {
        "description": "Plant-based medicine using herbs, roots, and botanicals",
        "key_concepts": ["Phytotherapy", "Tinctures", "Teas", "Topical applications", "Plant constituents"]
    },
    "homeopathy": {
        "description": "System based on 'like cures like' using highly diluted substances",
        "key_concepts": ["Similars", "Dilution", "Potency", "Remedies", "Constitutional treatment"]
    },
    "chiropractic": {
        "description": "Focus on spinal alignment and nervous system function",
        "key_concepts": ["Spinal adjustment", "Subluxation", "Nervous system", "Alignment", "Mobility"]
    },
    "nutrition": {
        "description": "Using food as medicine and nutritional interventions",
        "key_concepts": ["Macronutrients", "Micronutrients", "Food sensitivities", "Therapeutic diet", "Supplements"]
    },
    "vibrational": {
        "description": "Energy-based healing including sound, light, and frequency",
        "key_concepts": ["Frequency", "Energy fields", "Sound healing", "Crystal therapy", "Chakras"]
    }
}
