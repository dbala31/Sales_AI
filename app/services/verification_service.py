from typing import Dict, List, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session
from app.models import Contact, Batch, VerificationResult
from app.services.salesforce_service import SalesforceService
from app.services.mock_salesforce_service import MockSalesforceService
from app.core.config import settings
import asyncio
import json


class VerificationService:
    """Simplified service for contact deduplication against Salesforce"""
    
    def __init__(self, db: Session):
        self.db = db
        # Use mock Salesforce service if no credentials provided
        if all([settings.salesforce_username, settings.salesforce_password, settings.salesforce_security_token]):
            self.salesforce_service = SalesforceService()
        else:
            self.salesforce_service = MockSalesforceService()
    
    async def verify_contact(self, contact: Contact) -> Dict[str, Any]:
        """Check if contact is a duplicate in Salesforce"""
        verification_results = {
            "contact_id": contact.id,
            "email": contact.email,
            "verification_stages": {},
            "final_result": {}
        }
        
        try:
            logger.info(f"Checking duplicate for contact {contact.id}: {contact.email}")
            
            # Data completeness check
            if not contact.email and not contact.phone:
                contact.verification_status = "failed"
                contact.verification_errors = "Missing required data (email or phone)"
                self.db.commit()
                verification_results["final_result"] = {
                    "decision": "failed",
                    "reason": "Missing required data (email or phone)",
                    "should_include": False,
                    "is_duplicate": False
                }
                return verification_results
            
            # Check Salesforce for duplicates
            salesforce_result = await self._verify_salesforce(contact)
            verification_results["verification_stages"]["salesforce"] = salesforce_result
            
            # Make final decision based on duplicate check
            final_result = self._make_final_decision(salesforce_result)
            verification_results["final_result"] = final_result
            
            # Update contact record
            self._update_contact_record(contact, verification_results)
            
            logger.info(f"Duplicate check completed for contact {contact.id}: {final_result['decision']}")
            
        except Exception as e:
            logger.error(f"Duplicate check failed for contact {contact.id}: {str(e)}")
            contact.verification_status = "failed"
            contact.verification_errors = str(e)
            self.db.commit()
            verification_results["error"] = str(e)
        
        return verification_results
    
    
    
    
    
    
    async def _verify_salesforce(self, contact: Contact) -> Dict[str, Any]:
        """Verify contact through Salesforce"""
        try:
            result = await self.salesforce_service.verify_contact(
                email=contact.email,
                phone=contact.phone
            )
            
            # Store verification result
            verification_record = VerificationResult(
                contact_id=contact.id,
                source="salesforce",
                verification_successful=result.get("verified", False),
                confidence_score=1.0 if result.get("verified") else 0.0,
                result_data=json.dumps(result),
                error_message=result.get("error")
            )
            self.db.add(verification_record)
            
            return result
            
        except Exception as e:
            logger.error(f"Salesforce verification failed for contact {contact.id}: {str(e)}")
            return {
                "verified": False,
                "error": str(e),
                "is_duplicate": False
            }
    
    
    
    def _make_final_decision(self, salesforce_result: Dict) -> Dict[str, Any]:
        """Make final decision based on Salesforce duplicate check"""
        
        # Check if contact is a duplicate in Salesforce
        if salesforce_result.get("is_duplicate"):
            return {
                "decision": "duplicate",
                "reason": "Contact already exists in Salesforce",
                "should_include": False,
                "is_duplicate": True,
                "match_type": salesforce_result.get("match_type", "unknown")
            }
        
        # Contact is not a duplicate, include it
        return {
            "decision": "verified",
            "reason": "Contact not found in Salesforce - new contact",
            "should_include": True,
            "is_duplicate": False,
            "match_type": "new_contact"
        }
    
    def _update_contact_record(self, contact: Contact, verification_results: Dict):
        """Update contact record with verification results"""
        final_result = verification_results.get("final_result", {})
        salesforce_result = verification_results.get("verification_stages", {}).get("salesforce", {})
        
        # Update contact fields
        contact.is_verified = final_result.get("should_include", False)
        contact.verification_status = final_result.get("decision", "failed")
        contact.salesforce_verified = salesforce_result.get("verified", False)
        
        # Store Salesforce match data if found
        if salesforce_result.get("contact_data"):
            contact.salesforce_match_data = json.dumps(salesforce_result["contact_data"])
        
        # Store verification result in database
        verification_record = VerificationResult(
            contact_id=contact.id,
            source="salesforce_duplicate_check",
            verification_successful=not final_result.get("is_duplicate", True),
            confidence_score=1.0 if salesforce_result.get("verified") else 0.0,
            result_data=json.dumps(salesforce_result),
            error_message=salesforce_result.get("error")
        )
        self.db.add(verification_record)
        
        self.db.commit()
    
    async def verify_batch(self, batch_id: int) -> Dict[str, Any]:
        """Verify all contacts in a batch"""
        batch = self.db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        contacts = self.db.query(Contact).filter(Contact.batch_id == batch_id).all()
        batch.total_contacts = len(contacts)
        batch.status = "processing"
        self.db.commit()
        
        logger.info(f"Starting verification for batch {batch_id} with {len(contacts)} contacts")
        
        verified_count = 0
        failed_count = 0
        
        for i, contact in enumerate(contacts):
            try:
                result = await self.verify_contact(contact)
                
                if result.get("final_result", {}).get("should_include"):
                    verified_count += 1
                else:
                    failed_count += 1
                
                # Update batch progress
                batch.processed_contacts = i + 1
                batch.verified_contacts = verified_count
                batch.failed_contacts = failed_count
                batch.update_progress()
                self.db.commit()
                
                # Small delay to avoid overwhelming APIs
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error verifying contact {contact.id}: {str(e)}")
                failed_count += 1
                contact.verification_status = "failed"
                contact.verification_errors = str(e)
                self.db.commit()
        
        # Mark batch as completed
        batch.status = "completed"
        batch.processed_contacts = len(contacts)
        batch.verified_contacts = verified_count
        batch.failed_contacts = failed_count
        batch.update_progress()
        self.db.commit()
        
        logger.info(f"Batch {batch_id} verification completed: {verified_count} verified, {failed_count} failed")
        
        return {
            "batch_id": batch_id,
            "total_contacts": len(contacts),
            "verified_contacts": verified_count,
            "failed_contacts": failed_count,
            "success_rate": (verified_count / len(contacts)) * 100 if contacts else 0
        }