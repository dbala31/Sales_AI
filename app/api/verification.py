from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from loguru import logger

from app.core.database import get_db
from app.models import Contact, Batch
from app.services.verification_service import VerificationService
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/api/verification", tags=["verification"])


class ContactVerificationRequest(BaseModel):
    email: str
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None


class BatchVerificationRequest(BaseModel):
    contacts: List[ContactVerificationRequest]


@router.post("/single", response_model=Dict[str, Any])
async def verify_single_contact(
    request: ContactVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify a single contact"""
    try:
        # Create temporary batch for single contact
        batch = Batch(
            filename="single_contact_verification",
            total_contacts=1,
            status="processing"
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        # Create contact record
        contact = Contact(
            batch_id=batch.id,
            email=request.email,
            phone=request.phone,
            first_name=request.first_name,
            last_name=request.last_name,
            company=request.company,
            job_title=request.job_title,
            linkedin_url=request.linkedin_url
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        
        # Verify contact
        verification_service = VerificationService(db)
        result = await verification_service.verify_contact(contact)
        
        # Get updated contact data
        db.refresh(contact)
        
        return {
            "contact": contact.to_dict(),
            "verification_result": result
        }
        
    except Exception as e:
        logger.error(f"Single contact verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=Dict[str, Any])
async def verify_batch_contacts(
    request: BatchVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify multiple contacts"""
    try:
        if len(request.contacts) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 contacts per batch")
        
        # Create batch
        batch = Batch(
            filename="api_batch_verification",
            total_contacts=len(request.contacts),
            status="processing"
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        # Create contact records
        for contact_data in request.contacts:
            contact = Contact(
                batch_id=batch.id,
                email=contact_data.email,
                phone=contact_data.phone,
                first_name=contact_data.first_name,
                last_name=contact_data.last_name,
                company=contact_data.company,
                job_title=contact_data.job_title,
                linkedin_url=contact_data.linkedin_url
            )
            db.add(contact)
        
        db.commit()
        
        # Verify batch
        verification_service = VerificationService(db)
        result = await verification_service.verify_batch(batch.id)
        
        return {
            "batch_id": batch.id,
            "verification_result": result
        }
        
    except Exception as e:
        logger.error(f"Batch verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contact/{contact_id}", response_model=Dict[str, Any])
async def get_contact_verification(contact_id: int, db: Session = Depends(get_db)):
    """Get verification details for a specific contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {
        "contact": contact.to_dict(),
        "verification_results": [vr.to_dict() for vr in contact.verification_results]
    }


@router.post("/contact/{contact_id}/reverify")
async def reverify_contact(contact_id: int, db: Session = Depends(get_db)):
    """Re-verify a specific contact"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    try:
        # Reset verification status
        contact.verification_status = "pending"
        contact.is_verified = False
        contact.verification_errors = None
        db.commit()
        
        # Re-verify
        verification_service = VerificationService(db)
        result = await verification_service.verify_contact(contact)
        
        db.refresh(contact)
        
        return {
            "contact": contact.to_dict(),
            "verification_result": result
        }
        
    except Exception as e:
        logger.error(f"Contact re-verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/{batch_id}/analyze", response_model=Dict[str, Any])
async def analyze_batch_with_gemini(batch_id: int, db: Session = Depends(get_db)):
    """Analyze batch results using Gemini AI"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    try:
        # Get batch contacts
        contacts = db.query(Contact).filter(Contact.batch_id == batch_id).all()
        
        # Convert to analysis format
        batch_data = []
        for contact in contacts:
            batch_data.append({
                "email": contact.email,
                "company": contact.company,
                "is_verified": contact.is_verified,
                "quality_score": contact.quality_score,
                "verification_status": contact.verification_status
            })
        
        # Analyze with Gemini
        gemini_service = GeminiService()
        analysis = await gemini_service.analyze_batch_insights(batch_data)
        
        return {
            "batch_id": batch_id,
            "analysis": analysis,
            "contact_count": len(contacts)
        }
        
    except Exception as e:
        logger.error(f"Gemini analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=Dict[str, Any])
async def get_verification_statistics(db: Session = Depends(get_db)):
    """Get verification statistics for the most recent batch"""
    
    # Get the most recent batch
    latest_batch = db.query(Batch).order_by(Batch.created_at.desc()).first()
    
    if not latest_batch:
        return {
            "batch_info": {
                "batch_id": None,
                "filename": "No batches uploaded",
                "status": "none"
            },
            "contacts": {
                "total": 0,
                "verified": 0,
                "failed": 0,
                "verification_rate": 0.0
            },
            "quality_scores": {
                "average": 0,
                "minimum": 0,
                "maximum": 0
            }
        }
    
    # Get contact statistics for the latest batch only
    batch_contacts = db.query(Contact).filter(Contact.batch_id == latest_batch.id)
    total_contacts = batch_contacts.count()
    verified_contacts = batch_contacts.filter(Contact.is_verified == True).count()
    failed_contacts = batch_contacts.filter(Contact.verification_status == "failed").count()
    
    # Calculate verification rate for this batch
    verification_rate = (verified_contacts / total_contacts * 100) if total_contacts > 0 else 0
    
    # Get quality score statistics for this batch only
    from sqlalchemy import func
    quality_stats = batch_contacts.with_entities(
        func.avg(Contact.quality_score).label('avg_score'),
        func.min(Contact.quality_score).label('min_score'),
        func.max(Contact.quality_score).label('max_score')
    ).filter(Contact.quality_score > 0).first()
    
    return {
        "batch_info": {
            "batch_id": latest_batch.id,
            "filename": latest_batch.filename,
            "status": latest_batch.status,
            "upload_time": latest_batch.created_at.isoformat() if latest_batch.created_at else None
        },
        "contacts": {
            "total": total_contacts,
            "verified": verified_contacts,
            "failed": failed_contacts,
            "verification_rate": round(verification_rate, 2)
        },
        "quality_scores": {
            "average": round(quality_stats.avg_score or 0, 2),
            "minimum": quality_stats.min_score or 0,
            "maximum": quality_stats.max_score or 0
        }
    }