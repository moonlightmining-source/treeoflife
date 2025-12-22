from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Boolean, Text, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from datetime import datetime, timedelta
import os
import jwt
import bcrypt
import anthropic
import stripe  # ✅ STRIPE
import base64
import json
import secrets
from typing import Optional, List, Dict

# ==================== CONFIGURATION ====================

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')  # ✅ STRIPE KEY
stripe.api_key = STRIPE_SECRET_KEY  # ✅ Initialize Stripe

# ==================== STRIPE PRICE IDS ====================
STRIPE_PRICES = {
    'basic': os.getenv('STRIPE_PRICE_BASIC'),
    'premium': os.getenv('STRIPE_PRICE_PREMIUM'),
    'pro': os.getenv('STRIPE_PRICE_PRO')
}

# ==================== DATABASE SETUP ====================

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ==================== MODELS ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    subscription_tier = Column(String, default='free')
    family_member_limit = Column(Integer, default=0)
    stripe_customer_id = Column(String)  # ✅ STRIPE CUSTOMER ID
    stripe_subscription_id = Column(String)  # ✅ STRIPE SUBSCRIPTION ID
    created_at = Column(DateTime, default=datetime.utcnow)

class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    relationship = Column(String)
    age = Column(Integer)
    gender = Column(String)
    notes = Column(Text)
    date_of_birth = Column(Date)
    conversation_count = Column(Integer, default=0)
    has_health_profile = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class HealthProfile(Base):
    __tablename__ = "health_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), unique=True)
    
    # ==================== BASIC INFORMATION ====================
    full_name = Column(String)
    date_of_birth = Column(Date)
    sex = Column(String)
    blood_type = Column(String)
    height_inches = Column(Integer)
    weight = Column(Integer)
    ethnicity = Column(String)
    emergency_contact_name = Column(String)
    emergency_contact_phone = Column(String)
    
    # ==================== ALTERNATIVE MEDICINE ====================
    ayurvedic_dosha = Column(String)
    tcm_pattern = Column(String)
    
    # ==================== LIFESTYLE & WELLNESS ====================
    diet_type = Column(String)
    sleep_hours = Column(Float)
    stress_level = Column(Integer)
    preferred_traditions = Column(JSON)
    
    # ==================== MEDICAL HISTORY ====================
    current_conditions = Column(JSON)
    allergies = Column(JSON)
    past_diagnoses = Column(JSON)
    medications = Column(JSON)
    
    # ==================== METADATA ====================
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== DATABASE MIGRATION ====================

def run_migration():
    """Run database migration to add new health profile fields and fix user table columns"""
    print("🔧 Running database migration...")
    
    try:
        with engine.connect() as conn:
            # ==================== FIX 1: USERS TABLE - ALL COLUMNS ====================
            print("👤 Checking users table columns...")
            
            # Add all missing columns to users table
            user_migrations = [
                ("hashed_password", "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)"),
                ("full_name", "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)"),
                ("subscription_tier", "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free'"),
                ("family_member_limit", "ALTER TABLE users ADD COLUMN IF NOT EXISTS family_member_limit INTEGER DEFAULT 0"),
                ("stripe_customer_id", "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)"),
                ("stripe_subscription_id", "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)"),
                ("created_at", "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ]
            
            for col_name, query in user_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                    print(f"  ✅ Checked {col_name}")
                except Exception as e:
                    print(f"  ⚠️  {col_name}: {e}")
            
            # Check if we need to rename password columns
            check_password = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'password'
            """)).fetchone()
            
            if check_password:
                print("  📝 Renaming 'password' to 'hashed_password'...")
                conn.execute(text("ALTER TABLE users RENAME COLUMN password TO hashed_password"))
                conn.commit()
                print("  ✅ Renamed password column!")
            
            check_password_hash = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'password_hash'
            """)).fetchone()
            
            if check_password_hash:
                print("  📝 Renaming 'password_hash' to 'hashed_password'...")
                conn.execute(text("ALTER TABLE users RENAME COLUMN password_hash TO hashed_password"))
                conn.commit()
                print("  ✅ Renamed password_hash column!")
            
            print("✅ Users table updated!")
            
            # ==================== FIX 2: FAMILY MEMBERS TABLE ====================
            print("👨‍👩‍👧‍👦 Checking family members fields...")
            
            family_migrations = [
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS age INTEGER",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS gender VARCHAR(50)",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS notes TEXT",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS conversation_count INTEGER DEFAULT 0",
                "ALTER TABLE family_members ADD COLUMN IF NOT EXISTS has_health_profile BOOLEAN DEFAULT FALSE"
            ]
            
            for query in family_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"  ⚠️  Family member note: {e}")
            
            print("✅ Family members fields checked!")
            
            # ==================== FIX 3: HEALTH PROFILE FIELDS ====================
            print("🏥 Checking health profile fields...")
            
            health_migrations = [
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS date_of_birth DATE",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS sex VARCHAR(50)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS blood_type VARCHAR(10)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS height_inches INTEGER",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS weight INTEGER",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS ethnicity VARCHAR(100)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(255)",
                "ALTER TABLE health_profiles ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(20)"
            ]
            
            for query in health_migrations:
                try:
                    conn.execute(text(query))
                    conn.commit()
                except Exception as e:
                    print(f"  ⚠️  Health profile note: {e}")
            
            print("✅ Health profile fields checked!")
            print("✅ Database migration completed!")
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        raise

# ==================== FASTAPI APP ====================

app = FastAPI(title="Tree of Life AI API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== STARTUP EVENT ====================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("🌳 Starting Tree of Life AI...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
    
    # Run migration
    run_migration()
    
    print("🚀 Tree of Life AI is ready!")

# ==================== HELPER FUNCTIONS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {
        'user_id': str(user_id),
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(request: Request) -> str:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth_header.split(' ')[1]
    return verify_token(token)

def get_or_create_health_profile(db, user_id):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    if not profile:
        profile = HealthProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

# ==================== AUTH ENDPOINTS ====================

class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    zip_code: Optional[str] = None
    terms_accepted: bool = True

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
async def register(request: SignupRequest):
    with get_db_context() as db:
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
            full_name=request.name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        token = create_token(user.id)
        return {"token": token, "user": {"email": user.email, "name": user.full_name}}

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    with get_db_context() as db:
        user = db.query(User).filter(User.email == request.email).first()
        if not user or not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token(user.id)
        return {"token": token, "user": {"email": user.email, "name": user.full_name}}

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current user info including subscription tier"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "subscription_tier": user.subscription_tier,
            "family_member_limit": user.family_member_limit
        }

# ==================== FAMILY MEMBER ENDPOINTS ====================

class FamilyMemberCreate(BaseModel):
    name: str
    relationship: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    notes: Optional[str] = None
    date_of_birth: Optional[str] = None

@app.get("/api/family/members")  # ✅ CORRECT PATH
async def get_family_members(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        members = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).all()
        return {"members": [{
            "id": str(m.id),
            "name": m.name,
            "relationship": m.relationship,
            "age": m.age,
            "gender": m.gender,
            "notes": m.notes,
            "date_of_birth": m.date_of_birth.isoformat() if m.date_of_birth else None,
            "conversation_count": m.conversation_count or 0,
            "has_health_profile": m.has_health_profile or False
        } for m in members]}

@app.post("/api/family/members")  # ✅ CORRECT PATH
async def create_family_member(request: Request, member: FamilyMemberCreate):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        # Check limit
        user = db.query(User).filter(User.id == user_id).first()
        count = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).count()
        
        if count >= user.family_member_limit:
            raise HTTPException(status_code=403, detail="Family member limit reached")
        
        new_member = FamilyMember(
            user_id=user_id,
            name=member.name,
            relationship=member.relationship,
            age=member.age,
            gender=member.gender,
            notes=member.notes,
            date_of_birth=member.date_of_birth if member.date_of_birth else None
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        
        return {"id": new_member.id, "name": new_member.name}

@app.put("/api/family/members/{member_id}")  # ✅ CORRECT PATH
async def update_family_member(request: Request, member_id: int, member: FamilyMemberCreate):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        existing = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Member not found")
        
        existing.name = member.name
        existing.relationship = member.relationship
        existing.age = member.age
        existing.gender = member.gender
        existing.notes = member.notes
        if member.date_of_birth:
            existing.date_of_birth = member.date_of_birth
        
        db.commit()
        return {"success": True}

@app.delete("/api/family/members/{member_id}")  # ✅ CORRECT PATH
async def delete_family_member(request: Request, member_id: int):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user_id
        ).first()
        
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        db.delete(member)
        db.commit()
        
        return {"success": True}

# ==================== SUBSCRIPTION ENDPOINTS ====================

@app.get("/api/subscription/status")
async def get_subscription_status(request: Request):
    """Get user's current subscription status"""
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "tier": user.subscription_tier or 'free',
            "family_member_limit": user.family_member_limit or 0,
            "messages_this_month": 0  # Add message tracking later
        }

@app.post("/api/subscription/create-checkout")
async def create_checkout_session(request: Request):
    """Create Stripe checkout session"""
    user_id = get_current_user_id(request)
    data = await request.json()
    tier = data.get('tier')
    
    if tier not in STRIPE_PRICES:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    price_id = STRIPE_PRICES[tier]
    if not price_id:
        raise HTTPException(status_code=500, detail=f"Stripe price not configured for {tier}")
    
    with get_db_context() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create or get Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={'user_id': str(user.id)}
            )
            user.stripe_customer_id = customer.id
            db.commit()
        
        # Create checkout session
        try:
            checkout_session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='https://treeoflifeai.com/subscriptions?success=true',
                cancel_url='https://treeoflifeai.com/subscriptions',
                client_reference_id=str(user.id),
                metadata={
                    'user_id': str(user.id),
                    'tier': tier
                }
            )
            
            return {"checkout_url": checkout_session.url}
        
        except Exception as e:
            print(f"❌ Stripe error: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

@app.post("/api/subscription/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        tier = session.get('metadata', {}).get('tier')
        subscription_id = session.get('subscription')
        
        if user_id and tier:
            with get_db_context() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.subscription_tier = tier
                    user.stripe_subscription_id = subscription_id
                    
                    # Set family member limits
                    if tier == 'basic':
                        user.family_member_limit = 1
                    elif tier == 'premium':
                        user.family_member_limit = 5
                    elif tier == 'pro':
                        user.family_member_limit = 999
                    
                    db.commit()
                    print(f"✅ Updated user {user_id} to {tier}")
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        
        with get_db_context() as db:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                user.subscription_tier = 'free'
                user.family_member_limit = 0
                user.stripe_subscription_id = None
                db.commit()
                print(f"✅ Downgraded user to free")
    
    return {"status": "success"}

# ==================== HEALTH PROFILE ENDPOINTS ====================

@app.get("/api/health/profile")
async def get_health_profile(request: Request):
    user_id = get_current_user_id(request)
    
    with get_db_context() as db:
        profile = get_or_create_health_profile(db, user_id)
        
        # Calculate age if DOB exists
        age = None
        if profile.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - profile.date_of_birth.year
            if (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day):
                age -= 1
        
        return {
            "profile": {
                # Basic Information
                "full_name": profile.full_name,
                "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                "age": age,
                "sex": profile.sex,
                "blood_type": profile.blood_type,
                "height_inches": profile.height_inches,
                "weight": profile.weight,
                "ethnicity": profile.ethnicity,
                "emergency_contact_name": profile.emergency_contact_name,
                "emergency_contact_phone": profile.emergency_contact_phone,
                
                # Alternative Medicine
                "ayurvedic_dosha": profile.ayurvedic_dosha,
                "tcm_pattern": profile.tcm_pattern,
                
                # Lifestyle
                "diet_type": profile.diet_type,
                "sleep_hours": profile.sleep_hours,
                "stress_level": profile.stress_level,
                "preferred_traditions": profile.preferred_traditions or [],
                
                # Medical History
                "current_conditions": profile.current_conditions or [],
                "allergies": profile.allergies or [],
                "past_diagnoses": profile.past_diagnoses or [],
                "medications": profile.medications or []
            }
        }

@app.put("/api/health/profile")
async def update_health_profile(request: Request):
    user_id = get_current_user_id(request)
    data = await request.json()
    
    with get_db_context() as db:
        profile = get_or_create_health_profile(db, user_id)
        
        # Update all fields
        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        profile.updated_at = datetime.utcnow()
        db.commit()
        
        return {"success": True}

# ==================== LAB RESULTS ENDPOINTS ====================

@app.post("/api/lab-results/upload")
async def upload_lab_result(
    request: Request,
    file: UploadFile = File(...),
    provider: str = Form(...),
    test_date: str = Form(...)
):
    user_id = get_current_user_id(request)
    
    # Read file
    file_content = await file.read()
    
    # Convert to base64 for Claude
    base64_content = base64.b64encode(file_content).decode('utf-8')
    
    # Determine media type
    media_type = file.content_type
    if file.filename.lower().endswith('.pdf'):
        media_type = "application/pdf"
    elif file.filename.lower().endswith(('.jpg', '.jpeg')):
        media_type = "image/jpeg"
    elif file.filename.lower().endswith('.png'):
        media_type = "image/png"
    
    # Use Claude to extract values
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    if media_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_content
            }
        }
    else:
        content_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_content
            }
        }
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                content_block,
                {
                    "type": "text",
                    "text": """Extract ALL lab test results from this medical document. Return ONLY a JSON object with this exact structure:

{
  "test_type": "Type of test panel (e.g., Complete Blood Count, Metabolic Panel, Lipid Panel)",
  "results": [
    {
      "name": "Test name",
      "value": "Numeric value only",
      "unit": "Unit of measurement",
      "reference_range": "Normal range (e.g., 70-100 or <200)"
    }
  ]
}

Extract EVERY test result you can find. Be thorough. Return ONLY valid JSON, no other text."""
                }
            ]
        }]
    )
    
    # Parse response
    response_text = message.content[0].text
    
    # Clean up response
    if '```json' in response_text:
        response_text = response_text.split('```json')[1].split('```')[0]
    elif '```' in response_text:
        response_text = response_text.split('```')[1].split('```')[0]
    
    extracted_data = json.loads(response_text.strip())
    
    # Add metadata
    extracted_data['provider'] = provider
    extracted_data['test_date'] = test_date
    extracted_data['file_url'] = f"uploaded/{file.filename}"
    
    return extracted_data

@app.post("/api/lab-results/save")
async def save_lab_results(request: Request):
    user_id = get_current_user_id(request)
    data = await request.json()
    
    with engine.connect() as conn:
        # Create table if doesn't exist
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lab_results (
                id SERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                test_type VARCHAR(255),
                test_date DATE,
                provider VARCHAR(255),
                file_url TEXT,
                results JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        
        # Insert result
        conn.execute(text("""
            INSERT INTO lab_results (user_id, test_type, test_date, provider, file_url, results)
            VALUES (:user_id, :test_type, :test_date, :provider, :file_url, :results)
        """), {
            'user_id': str(user_id),
            'test_type': data.get('test_type'),
            'test_date': data.get('test_date'),
            'provider': data.get('provider'),
            'file_url': data.get('file_url'),
            'results': json.dumps(data.get('results', []))
        })
        conn.commit()
    
    return {"success": True}

@app.get("/api/lab-results")
async def get_lab_results(request: Request):
    user_id = get_current_user_id(request)
    
    with engine.connect() as conn:
        results = conn.execute(text("""
            SELECT id, test_type, test_date, provider, results, created_at
            FROM lab_results
            WHERE user_id = :user_id
            ORDER BY test_date DESC
        """), {'user_id': str(user_id)})
        
        return [{
            'id': row[0],
            'test_type': row[1],
            'test_date': row[2].isoformat() if row[2] else None,
            'provider': row[3],
            'results': row[4] if isinstance(row[4], list) else json.loads(row[4]) if row[4] else [],
            'created_at': row[5].isoformat() if row[5] else None
        } for row in results]

@app.delete("/api/lab-results/{result_id}")
async def delete_lab_result(request: Request, result_id: int):
    user_id = get_current_user_id(request)
    
    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM lab_results
            WHERE id = :id AND user_id = :user_id
        """), {'id': result_id, 'user_id': str(user_id)})
        conn.commit()
    
    return {"success": True}

# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Tree of Life AI API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
