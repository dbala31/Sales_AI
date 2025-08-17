from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import uuid
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.models import Batch, Contact
from app.utils.csv_processor import CSVProcessor
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/csv", response_model=Dict[str, Any])
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process CSV file for contact verification"""
    
    # Validate file
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    if file.size > settings.max_file_size:
        raise HTTPException(status_code=400, detail="File size exceeds limit")
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(settings.upload_directory, filename)
        
        # Ensure upload directory exists
        os.makedirs(settings.upload_directory, exist_ok=True)
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"File uploaded: {filename}")
        
        # Process CSV
        processor = CSVProcessor()
        df, stats = processor.process_csv(file_path)
        contacts_data = processor.convert_to_contact_records(df)
        
        # Create batch record
        batch = Batch(
            filename=file.filename,
            total_contacts=len(contacts_data),
            status="uploaded"
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        # Create contact records
        for contact_data in contacts_data:
            contact = Contact(
                batch_id=batch.id,
                **contact_data
            )
            db.add(contact)
        
        db.commit()
        
        logger.info(f"Created batch {batch.id} with {len(contacts_data)} contacts")
        
        # Start verification in background
        background_tasks.add_task(verify_batch_background, batch.id, db)
        
        return {
            "batch_id": batch.id,
            "filename": file.filename,
            "total_contacts": len(contacts_data),
            "processing_stats": stats,
            "status": "processing_started"
        }
        
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


async def verify_batch_background(batch_id: int, db: Session):
    """Background task to verify batch contacts"""
    try:
        verification_service = VerificationService(db)
        result = await verification_service.verify_batch(batch_id)
        logger.info(f"Background verification completed for batch {batch_id}: {result}")
    except Exception as e:
        logger.error(f"Background verification failed for batch {batch_id}: {str(e)}")
        # Update batch status to failed
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            batch.status = "failed"
            batch.processing_errors = str(e)
            db.commit()


@router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: int, db: Session = Depends(get_db)):
    """Get processing status of a batch"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return batch.to_dict()


@router.get("/batch/{batch_id}/contacts")
async def get_batch_contacts(
    batch_id: int, 
    skip: int = 0, 
    limit: int = 100,
    verified_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get contacts from a batch"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    query = db.query(Contact).filter(Contact.batch_id == batch_id)
    
    if verified_only:
        query = query.filter(Contact.is_verified == True)
    
    contacts = query.offset(skip).limit(limit).all()
    
    return {
        "batch_id": batch_id,
        "contacts": [contact.to_dict() for contact in contacts],
        "total": query.count()
    }


@router.get("/batch/{batch_id}/download")
async def download_verified_contacts(batch_id: int, db: Session = Depends(get_db)):
    """Download verified contacts as CSV"""
    from fastapi.responses import FileResponse
    import tempfile
    
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Get verified contacts
    contacts = db.query(Contact).filter(
        Contact.batch_id == batch_id,
        Contact.is_verified == True
    ).all()
    
    if not contacts:
        raise HTTPException(status_code=404, detail="No verified contacts found")
    
    # Convert to CSV format
    contacts_data = []
    for contact in contacts:
        contacts_data.append({
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "phone": contact.phone,
            "company": contact.company,
            "job_title": contact.job_title,
            "linkedin_url": contact.linkedin_url,
            "quality_score": contact.quality_score,
            "verification_status": contact.verification_status
        })
    
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
        processor = CSVProcessor()
        processor.export_to_csv(contacts_data, tmp_file.name)
        
        return FileResponse(
            tmp_file.name,
            media_type='text/csv',
            filename=f"verified_contacts_batch_{batch_id}.csv"
        )