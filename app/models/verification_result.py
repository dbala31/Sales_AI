from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class VerificationResult(Base):
    __tablename__ = "verification_results"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    
    # Verification source
    source = Column(String(50), nullable=False)  # linkedin, salesforce, ai_scoring
    
    # Result data
    verification_successful = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    result_data = Column(Text)  # JSON string with detailed results
    
    # Error information
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    contact = relationship("Contact", back_populates="verification_results")
    
    def to_dict(self):
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "source": self.source,
            "verification_successful": self.verification_successful,
            "confidence_score": self.confidence_score,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }