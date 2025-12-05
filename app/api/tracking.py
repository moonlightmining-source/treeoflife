"""
Tracking API Routes - Symptoms and Treatments
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.symptom import Symptom
from app.models.treatment import Treatment


router = APIRouter()


# ==================== SYMPTOMS ====================

@router.post("/tracking/symptoms")
async def log_symptom(
    symptom_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log a new symptom
    """
    symptom = Symptom(
        user_id=current_user.id,
        symptom_name=symptom_data.get("symptom_name"),
        severity=symptom_data.get("severity"),
        description=symptom_data.get("description"),
        body_location=symptom_data.get("body_location"),
        started_at=symptom_data.get("started_at"),
        frequency=symptom_data.get("frequency")
    )
    
    db.add(symptom)
    db.commit()
    db.refresh(symptom)
    
    return {
        "success": True,
        "data": symptom.to_dict(),
        "message": "Symptom logged successfully"
    }


@router.get("/tracking/symptoms")
async def get_symptoms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all symptoms for current user
    """
    symptoms = db.query(Symptom).filter(
        Symptom.user_id == current_user.id
    ).order_by(Symptom.logged_at.desc()).all()
    
    return {
        "success": True,
        "data": [symptom.to_dict() for symptom in symptoms]
    }


@router.get("/tracking/symptoms/{symptom_id}")
async def get_symptom(
    symptom_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific symptom
    """
    symptom = db.query(Symptom).filter(
        Symptom.id == symptom_id,
        Symptom.user_id == current_user.id
    ).first()
    
    if not symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symptom not found"
        )
    
    return {
        "success": True,
        "data": symptom.to_dict()
    }


@router.put("/tracking/symptoms/{symptom_id}")
async def update_symptom(
    symptom_id: str,
    symptom_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a symptom
    """
    symptom = db.query(Symptom).filter(
        Symptom.id == symptom_id,
        Symptom.user_id == current_user.id
    ).first()
    
    if not symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symptom not found"
        )
    
    # Update fields
    for key, value in symptom_data.items():
        if hasattr(symptom, key):
            setattr(symptom, key, value)
    
    db.commit()
    db.refresh(symptom)
    
    return {
        "success": True,
        "data": symptom.to_dict(),
        "message": "Symptom updated successfully"
    }


@router.delete("/tracking/symptoms/{symptom_id}")
async def delete_symptom(
    symptom_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a symptom
    """
    symptom = db.query(Symptom).filter(
        Symptom.id == symptom_id,
        Symptom.user_id == current_user.id
    ).first()
    
    if not symptom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Symptom not found"
        )
    
    db.delete(symptom)
    db.commit()
    
    return {
        "success": True,
        "message": "Symptom deleted successfully"
    }


# ==================== TREATMENTS ====================

@router.post("/tracking/treatments")
async def log_treatment(
    treatment_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log a new treatment
    """
    treatment = Treatment(
        user_id=current_user.id,
        treatment_name=treatment_data.get("treatment_name"),
        treatment_type=treatment_data.get("treatment_type"),
        tradition=treatment_data.get("tradition"),
        dosage=treatment_data.get("dosage"),
        frequency=treatment_data.get("frequency"),
        started_at=treatment_data.get("started_at"),
        purpose=treatment_data.get("purpose")
    )
    
    db.add(treatment)
    db.commit()
    db.refresh(treatment)
    
    return {
        "success": True,
        "data": treatment.to_dict(),
        "message": "Treatment logged successfully"
    }


@router.get("/tracking/treatments")
async def get_treatments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all treatments for current user
    """
    treatments = db.query(Treatment).filter(
        Treatment.user_id == current_user.id
    ).order_by(Treatment.created_at.desc()).all()
    
    return {
        "success": True,
        "data": [treatment.to_dict() for treatment in treatments]
    }


@router.get("/tracking/treatments/{treatment_id}")
async def get_treatment(
    treatment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific treatment
    """
    treatment = db.query(Treatment).filter(
        Treatment.id == treatment_id,
        Treatment.user_id == current_user.id
    ).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    return {
        "success": True,
        "data": treatment.to_dict()
    }


@router.put("/tracking/treatments/{treatment_id}")
async def update_treatment(
    treatment_id: str,
    treatment_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a treatment
    """
    treatment = db.query(Treatment).filter(
        Treatment.id == treatment_id,
        Treatment.user_id == current_user.id
    ).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    # Update fields
    for key, value in treatment_data.items():
        if hasattr(treatment, key):
            setattr(treatment, key, value)
    
    db.commit()
    db.refresh(treatment)
    
    return {
        "success": True,
        "data": treatment.to_dict(),
        "message": "Treatment updated successfully"
    }


@router.delete("/tracking/treatments/{treatment_id}")
async def delete_treatment(
    treatment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a treatment
    """
    treatment = db.query(Treatment).filter(
        Treatment.id == treatment_id,
        Treatment.user_id == current_user.id
    ).first()
    
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found"
        )
    
    db.delete(treatment)
    db.commit()
    
    return {
        "success": True,
        "message": "Treatment deleted successfully"
    }
