from celery import current_task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.celery_app import celery_app
from app.core.config import settings
from app.services.verification_service import VerificationService
from app.models import Batch, Contact
from loguru import logger
import asyncio


# Create database session for tasks
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery_app.task(bind=True)
def verify_batch_task(self, batch_id: int):
    """Celery task to verify a batch of contacts"""
    db = SessionLocal()
    
    try:
        logger.info(f"Starting batch verification task for batch {batch_id}")
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'batch_id': batch_id, 'status': 'Starting verification'}
        )
        
        # Run verification (need to handle async in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        verification_service = VerificationService(db)
        result = loop.run_until_complete(verification_service.verify_batch(batch_id))
        
        loop.close()
        
        logger.info(f"Batch verification completed: {result}")
        
        return {
            'batch_id': batch_id,
            'status': 'completed',
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Batch verification task failed: {str(e)}")
        
        # Update batch status to failed
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            batch.status = "failed"
            batch.processing_errors = str(e)
            db.commit()
        
        self.update_state(
            state='FAILURE',
            meta={'batch_id': batch_id, 'error': str(e)}
        )
        
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True)
def verify_single_contact_task(self, contact_id: int):
    """Celery task to verify a single contact"""
    db = SessionLocal()
    
    try:
        logger.info(f"Starting single contact verification task for contact {contact_id}")
        
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")
        
        # Update task status
        self.update_state(
            state='PROGRESS',
            meta={'contact_id': contact_id, 'status': 'Verifying contact'}
        )
        
        # Run verification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        verification_service = VerificationService(db)
        result = loop.run_until_complete(verification_service.verify_contact(contact))
        
        loop.close()
        
        logger.info(f"Contact verification completed: {result}")
        
        return {
            'contact_id': contact_id,
            'status': 'completed',
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Contact verification task failed: {str(e)}")
        
        # Update contact status
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            contact.verification_status = "failed"
            contact.verification_errors = str(e)
            db.commit()
        
        self.update_state(
            state='FAILURE',
            meta={'contact_id': contact_id, 'error': str(e)}
        )
        
        raise
    
    finally:
        db.close()


@celery_app.task
def cleanup_old_batches():
    """Cleanup old batch data (runs periodically)"""
    db = SessionLocal()
    
    try:
        from datetime import datetime, timedelta
        
        # Delete batches older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        old_batches = db.query(Batch).filter(
            Batch.created_at < cutoff_date,
            Batch.status.in_(["completed", "failed"])
        ).all()
        
        deleted_count = 0
        for batch in old_batches:
            # Delete associated contacts first
            db.query(Contact).filter(Contact.batch_id == batch.id).delete()
            # Delete batch
            db.delete(batch)
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old batches")
        
        return {"deleted_batches": deleted_count}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        db.rollback()
        raise
    
    finally:
        db.close()


@celery_app.task
def generate_daily_report():
    """Generate daily verification report"""
    db = SessionLocal()
    
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Get yesterday's data
        yesterday = datetime.utcnow() - timedelta(days=1)
        start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get statistics
        daily_stats = db.query(
            func.count(Contact.id).label('total_contacts'),
            func.sum(func.case([(Contact.is_verified == True, 1)], else_=0)).label('verified'),
            func.sum(func.case([(Contact.verification_status == 'failed', 1)], else_=0)).label('failed'),
            func.avg(Contact.quality_score).label('avg_quality')
        ).filter(
            Contact.created_at >= start_of_day,
            Contact.created_at <= end_of_day
        ).first()
        
        batch_stats = db.query(
            func.count(Batch.id).label('total_batches'),
            func.sum(func.case([(Batch.status == 'completed', 1)], else_=0)).label('completed')
        ).filter(
            Batch.created_at >= start_of_day,
            Batch.created_at <= end_of_day
        ).first()
        
        report = {
            "date": yesterday.strftime("%Y-%m-%d"),
            "contacts": {
                "total": daily_stats.total_contacts or 0,
                "verified": daily_stats.verified or 0,
                "failed": daily_stats.failed or 0,
                "avg_quality": round(daily_stats.avg_quality or 0, 2)
            },
            "batches": {
                "total": batch_stats.total_batches or 0,
                "completed": batch_stats.completed or 0
            }
        }
        
        logger.info(f"Daily report generated: {report}")
        
        # Here you could send the report via email, store in database, etc.
        
        return report
        
    except Exception as e:
        logger.error(f"Daily report generation failed: {str(e)}")
        raise
    
    finally:
        db.close()


# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-batches': {
        'task': 'app.tasks.cleanup_old_batches',
        'schedule': 86400.0,  # Run daily (24 hours)
    },
    'generate-daily-report': {
        'task': 'app.tasks.generate_daily_report',
        'schedule': 3600.0,  # Run hourly to check for new day
    },
}