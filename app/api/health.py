"""
Health Profile API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.health_profile import HealthProfile


router = APIRouter()


@router.get("/health/profile")
async def get_health_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's health profile
    """
    profile = db.query(HealthProfile).filter(
        HealthProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        # Create empty profile if doesn't exist
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    return {
        "success": True,
        "data": profile.to_dict()
    }


@router.put("/health/profile")
async def update_health_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's health profile
    """
    profile = db.query(HealthProfile).filter(
        HealthProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)
    
    # Update fields
    for key, value in profile_data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    
    return {
        "success": True,
        "data": profile.to_dict(),
        "message": "Profile updated successfully"
    }


@router.post("/health/constitutional-assessment")
async def constitutional_assessment(
    answers: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate constitutional type from answers
    """
    # Simple dosha calculation
    scores = {"vata": 0, "pitta": 0, "kapha": 0}
    
    for answer in answers.values():
        if answer in scores:
            scores[answer] += 1
    
    # Determine primary dosha
    primary_dosha = max(scores, key=scores.get)
    
    # Update profile
    profile = db.query(HealthProfile).filter(
        HealthProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)
    
    profile.ayurvedic_dosha = primary_dosha
    db.commit()
    
    return {
        "success": True,
        "data": {
            "dosha": primary_dosha,
            "scores": scores
        }
    }


@router.get("/health/recommendations")
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized health recommendations
    """
    profile = db.query(HealthProfile).filter(
        HealthProfile.user_id == current_user.id
    ).first()
    
    if not profile or not profile.ayurvedic_dosha:
        return {
            "success": True,
            "data": {
                "message": "Complete your constitutional assessment to get personalized recommendations"
            }
        }
    
    # Basic recommendations based on dosha
    recommendations = {
        "vata": {
            "diet": "Warm, cooked foods; avoid cold and raw",
            "lifestyle": "Regular routine, adequate rest, calming activities",
            "herbs": "Ashwagandha, Brahmi, warming spices"
        },
        "pitta": {
            "diet": "Cooling foods; avoid spicy and acidic",
            "lifestyle": "Avoid overheating, moderate exercise, relaxation",
            "herbs": "Aloe, Coriander, cooling herbs"
        },
        "kapha": {
            "diet": "Light, warm, spicy foods; reduce dairy and sweets",
            "lifestyle": "Regular exercise, stay active, avoid oversleeping",
            "herbs": "Ginger, Turmeric, stimulating spices"
        }
    }
    
    return {
        "success": True,
        "data": {
            "dosha": profile.ayurvedic_dosha,
            "recommendations": recommendations.get(profile.ayurvedic_dosha, {})
        }
    }
