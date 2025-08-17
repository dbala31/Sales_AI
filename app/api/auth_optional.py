from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from datetime import datetime

from app.core.database import get_db
from app.models import User

security = HTTPBearer(auto_error=False)
SECRET_KEY = 'your-secret-key-change-in-production'
ALGORITHM = "HS256"


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user from JWT token, return None if not authenticated"""
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
    except jwt.PyJWTError:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
    
    return user