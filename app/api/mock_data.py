from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import pandas as pd
from loguru import logger

from app.core.database import get_db
from app.services.mock_salesforce_service import MockSalesforceService

router = APIRouter(prefix="/api/mock", tags=["mock-data"])


@router.post("/salesforce/upload")
async def upload_mock_salesforce_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Upload mock Salesforce data from CSV"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Save uploaded file
        file_path = f"data/uploaded_salesforce_{file.filename}"
        os.makedirs("data", exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Load into mock service
        mock_service = MockSalesforceService()
        mock_service.load_custom_data(file_path)
        
        # Get statistics
        stats = mock_service.get_statistics()
        
        logger.info(f"Uploaded mock Salesforce data: {file.filename}")
        
        return {
            "message": "Mock Salesforce data uploaded successfully",
            "filename": file.filename,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error uploading mock Salesforce data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/salesforce/statistics")
async def get_mock_salesforce_statistics() -> Dict[str, Any]:
    """Get statistics about mock Salesforce data"""
    try:
        mock_service = MockSalesforceService()
        stats = mock_service.get_statistics()
        
        return {
            "mock_data_statistics": stats,
            "data_files": {
                "contacts": "data/mock_salesforce_contacts.csv",
                "sample_input": "data/sample_input_contacts.csv"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting mock statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-verification/{email}")
async def test_contact_verification(email: str) -> Dict[str, Any]:
    """Test verification against mock Salesforce data"""
    try:
        mock_service = MockSalesforceService()
        result = await mock_service.verify_contact(email)
        
        return {
            "email": email,
            "verification_result": result
        }
        
    except Exception as e:
        logger.error(f"Error testing verification for {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sample-data/download")
async def download_sample_data():
    """Download sample CSV data for testing"""
    from fastapi.responses import FileResponse
    
    try:
        sample_file = "data/sample_input_contacts.csv"
        if os.path.exists(sample_file):
            return FileResponse(
                sample_file,
                media_type='text/csv',
                filename="sample_contacts.csv"
            )
        else:
            raise HTTPException(status_code=404, detail="Sample file not found")
            
    except Exception as e:
        logger.error(f"Error downloading sample data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))