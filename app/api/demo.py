from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User
from app.api.auth import hash_password
from loguru import logger

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/create-demo-user")
async def create_demo_user(db: Session = Depends(get_db)):
    """Create demo user for testing"""
    try:
        # Check if demo user already exists
        existing_user = db.query(User).filter(User.email == "demo@salesai.com").first()
        
        if existing_user:
            return {"message": "Demo user already exists", "user": existing_user.to_dict()}
        
        # Create demo user
        demo_user = User(
            email="demo@salesai.com",
            username="demo",
            hashed_password=hash_password("demo123"),
            first_name="Demo",
            last_name="User",
            is_active=True,
            is_verified=True
        )
        
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        
        logger.info("Demo user created successfully")
        
        return {
            "message": "Demo user created successfully",
            "user": demo_user.to_dict(),
            "credentials": {
                "email": "demo@salesai.com",
                "password": "demo123"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to create demo user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create demo user")