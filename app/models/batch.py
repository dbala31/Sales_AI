from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Batch(Base):
    __tablename__ = "batches"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), default="processing")  # processing, completed, failed, cancelled
    
    # Statistics
    total_contacts = Column(Integer, default=0)
    processed_contacts = Column(Integer, default=0)
    verified_contacts = Column(Integer, default=0)
    failed_contacts = Column(Integer, default=0)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    processing_errors = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    contacts = relationship("Contact", back_populates="batch", cascade="all, delete-orphan")
    
    @property
    def success_rate(self):
        if self.processed_contacts == 0:
            return 0.0
        return (self.verified_contacts / self.processed_contacts) * 100
    
    def update_progress(self):
        if self.total_contacts > 0:
            self.progress_percentage = (self.processed_contacts / self.total_contacts) * 100
        else:
            self.progress_percentage = 0.0
    
    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "total_contacts": self.total_contacts,
            "processed_contacts": self.processed_contacts,
            "verified_contacts": self.verified_contacts,
            "failed_contacts": self.failed_contacts,
            "progress_percentage": self.progress_percentage,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }