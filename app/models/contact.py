from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    
    # Raw data
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), index=True)
    phone = Column(String(50))
    company = Column(String(255))
    job_title = Column(String(255))
    linkedin_url = Column(String(500))
    
    # Verification status
    is_verified = Column(Boolean, default=False)
    quality_score = Column(Float, default=0.0)
    verification_status = Column(String(50), default="pending")  # pending, verified, failed, skipped
    
    # Verification results
    linkedin_verified = Column(Boolean, default=False)
    salesforce_verified = Column(Boolean, default=False)
    linkedin_profile_data = Column(Text)  # JSON string
    salesforce_match_data = Column(Text)  # JSON string
    
    # Error tracking
    verification_errors = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    batch = relationship("Batch", back_populates="contacts")
    verification_results = relationship("VerificationResult", back_populates="contact")
    
    @property
    def full_name(self):
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts))
    
    @property
    def is_complete(self):
        return bool(self.email and self.phone)
    
    def to_dict(self):
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "company": self.company,
            "job_title": self.job_title,
            "linkedin_url": self.linkedin_url,
            "is_verified": self.is_verified,
            "quality_score": self.quality_score,
            "verification_status": self.verification_status,
            "linkedin_verified": self.linkedin_verified,
            "salesforce_verified": self.salesforce_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }