# lab_results_endpoints.py
# ADD THIS FILE TO YOUR BACKEND FOLDER
# Then import it in your main.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Date, Float, Boolean, DateTime, ForeignKey, JSON
from typing import List
import os
import shutil
from datetime import datetime, date
import anthropic
import base64
import json

# Import your existing database and auth functions
# ADJUST THESE IMPORTS TO MATCH YOUR PROJECT:
from database import get_db, Base  # Your database setup
from auth import get_current_user   # Your auth function

# ============================================================================
# DATABASE MODEL
# ============================================================================

class LabResult(Base):
    __tablename__ = "lab_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Test metadata
    test_type = Column(String, nullable=False)
    test_date = Column(Date, nullable=False)
    provider = Column(String, nullable=False)
    
    # File storage
    original_file_path = Column(String)
    
    # Extracted results (JSON)
    results = Column(JSON)
    
    # AI extraction metadata
    extraction_confidence = Column(Float, default=0.0)
    manually_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================================================
# PYDANTIC MODELS (for API)
# ============================================================================

from pydantic import BaseModel

class LabResultValue(BaseModel):
    name: str
    value: str
    unit: str
    reference_range: str

class LabResultCreate(BaseModel):
    test_type: str
    test_date: str
    provider: str
    results: List[LabResultValue]
    file_url: str

class LabResultResponse(BaseModel):
    id: int
    test_type: str
    test_date: date
    provider: str
    results: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# AI EXTRACTION FUNCTION
# ============================================================================

async def extract_lab_data(file_path: str, provider: str, test_date: str) -> dict:
    """Extract lab test results from image/PDF using Claude Vision API"""
    
    try:
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise Exception("ANTHROPIC_API_KEY not found in environment")
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Read file and encode to base64
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        # Determine media type
        file_ext = os.path.splitext(file_path)[1].lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf'
        }
        media_type = media_type_map.get(file_ext, 'image/jpeg')
        
        # Create extraction prompt
        extraction_prompt = f"""You are an expert medical data extraction AI. Extract ALL lab test results from this medical document.

Provider: {provider}
Date: {test_date}

Extract and return ONLY valid JSON in this EXACT format (no markdown, no explanation):

{{
    "test_type": "Blood Panel",
    "test_date": "{test_date}",
    "provider": "{provider}",
    "results": [
        {{
            "name": "Glucose",
            "value": "95",
            "unit": "mg/dL",
            "reference_range": "70-100"
        }}
    ],
    "confidence": 0.95
}}

CRITICAL RULES:
1. Extract ALL visible test results
2. Use exact names from the document
3. Include units (mg/dL, %, etc.)
4. Include reference ranges if visible
5. Return ONLY the JSON object - no markdown formatting
6. If you can't find certain data, use empty string ""
7. For test_type, choose from: Blood Panel, Lipid Panel, Metabolic Panel, Thyroid Panel, Urinalysis, or Other

Extract now:"""

        # Call Claude API
        if file_ext == '.pdf':
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        },
                        {"type": "text", "text": extraction_prompt}
                    ]
                }]
            )
        else:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        },
                        {"type": "text", "text": extraction_prompt}
                    ]
                }]
            )
        
        # Extract response
        response_text = message.content[0].text.strip()
        
        # Clean JSON
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback data
            extracted_data = {
                "test_type": "Blood Panel",
                "test_date": test_date,
                "provider": provider,
                "results": [],
                "confidence": 0.0
            }
        
        return extracted_data
        
    except Exception as e:
        print(f"Extraction error: {e}")
        return {
            "test_type": "Blood Panel",
            "test_date": test_date,
            "provider": provider,
            "results": [],
            "confidence": 0.0,
            "error": str(e)
        }

# ============================================================================
# API ROUTER & ENDPOINTS
# ============================================================================

router = APIRouter(prefix="/api/lab-results", tags=["lab_results"])

# Upload directory
UPLOAD_DIR = "uploads/lab_results"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_lab_result(
    file: UploadFile = File(...),
    provider: str = Form(...),
    test_date: str = Form(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload lab result file and extract data using AI"""
    try:
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Create user directory
        user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = os.path.splitext(file.filename)[1]
        filename = f"{timestamp}{file_ext}"
        file_path = os.path.join(user_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract data using AI
        extracted_data = await extract_lab_data(file_path, provider, test_date)
        extracted_data['file_url'] = file_path
        
        return extracted_data
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save")
async def save_lab_result(
    data: LabResultCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save confirmed lab results to database"""
    try:
        results_json = [result.dict() for result in data.results]
        
        lab_result = LabResult(
            user_id=current_user.id,
            test_type=data.test_type,
            test_date=datetime.strptime(data.test_date, "%Y-%m-%d").date(),
            provider=data.provider,
            original_file_path=data.file_url,
            results=results_json,
            manually_verified=True,
            extraction_confidence=0.9
        )
        
        db.add(lab_result)
        db.commit()
        db.refresh(lab_result)
        
        return {
            "status": "success",
            "id": lab_result.id,
            "message": "Lab results saved successfully"
        }
        
    except Exception as e:
        db.rollback()
        print(f"Save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[LabResultResponse])
async def get_lab_results(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all lab results for current user"""
    try:
        results = db.query(LabResult).filter(
            LabResult.user_id == current_user.id
        ).order_by(LabResult.test_date.desc()).all()
        
        return results
        
    except Exception as e:
        print(f"Get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{result_id}")
async def delete_lab_result(
    result_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a lab result"""
    try:
        result = db.query(LabResult).filter(
            LabResult.id == result_id,
            LabResult.user_id == current_user.id
        ).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Lab result not found")
        
        if result.original_file_path and os.path.exists(result.original_file_path):
            os.remove(result.original_file_path)
        
        db.delete(result)
        db.commit()
        
        return {"status": "success", "message": "Lab result deleted"}
        
    except Exception as e:
        db.rollback()
        print(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
