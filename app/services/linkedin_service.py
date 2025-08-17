import asyncio
import time
from typing import Optional, Dict, Any
import httpx
from loguru import logger
from app.core.config import settings


class LinkedInService:
    """LinkedIn API integration for contact verification"""
    
    def __init__(self):
        self.client_id = settings.linkedin_client_id
        self.client_secret = settings.linkedin_client_secret
        self.access_token = settings.linkedin_access_token
        self.rate_limit = settings.linkedin_rate_limit
        self.request_count = 0
        self.last_reset = time.time()
        
        # Rate limiting
        self.requests_per_hour = self.rate_limit
        self.request_timestamps = []
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        
        # Remove requests older than 1 hour
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < 3600
        ]
        
        # If we've hit the rate limit, wait
        if len(self.request_timestamps) >= self.requests_per_hour:
            wait_time = 3600 - (current_time - self.request_timestamps[0])
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                self.request_timestamps = []
    
    async def verify_profile(self, email: str, name: str = None, company: str = None) -> Dict[str, Any]:
        """Verify LinkedIn profile by email"""
        try:
            await self._check_rate_limit()
            
            # Record this request
            self.request_timestamps.append(time.time())
            
            # Mock implementation - replace with actual LinkedIn API calls
            # Note: LinkedIn API has restrictions on email-based searches
            result = await self._mock_linkedin_verification(email, name, company)
            
            logger.info(f"LinkedIn verification completed for {email}")
            return result
            
        except Exception as e:
            logger.error(f"LinkedIn verification failed for {email}: {str(e)}")
            return {
                "verified": False,
                "error": str(e),
                "profile_data": None
            }
    
    async def _mock_linkedin_verification(self, email: str, name: str = None, company: str = None) -> Dict[str, Any]:
        """Mock LinkedIn verification for demonstration"""
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        # Mock verification logic
        # In production, this would make actual LinkedIn API calls
        domain = email.split('@')[1] if '@' in email else ""
        
        # Simulate higher success rate for business domains
        business_domains = ['company.com', 'corp.com', 'inc.com', 'business.com']
        is_business_domain = any(bd in domain for bd in business_domains)
        
        # Mock verification success based on email domain and other factors
        verification_score = 0.7 if is_business_domain else 0.4
        
        if name:
            verification_score += 0.2
        if company:
            verification_score += 0.1
        
        verified = verification_score > 0.6
        
        profile_data = None
        if verified:
            profile_data = {
                "profile_url": f"https://linkedin.com/in/{name.lower().replace(' ', '-')}" if name else None,
                "current_position": company,
                "industry": "Technology",
                "location": "United States",
                "connections": 500,
                "verified_email": True
            }
        
        return {
            "verified": verified,
            "confidence_score": verification_score,
            "profile_data": profile_data,
            "verification_method": "email_lookup"
        }
    
    async def verify_by_url(self, linkedin_url: str) -> Dict[str, Any]:
        """Verify LinkedIn profile by URL"""
        try:
            await self._check_rate_limit()
            self.request_timestamps.append(time.time())
            
            # Extract profile ID from URL
            profile_id = self._extract_profile_id(linkedin_url)
            if not profile_id:
                return {
                    "verified": False,
                    "error": "Invalid LinkedIn URL",
                    "profile_data": None
                }
            
            # Mock profile verification
            result = await self._mock_profile_verification(profile_id)
            
            logger.info(f"LinkedIn URL verification completed for {linkedin_url}")
            return result
            
        except Exception as e:
            logger.error(f"LinkedIn URL verification failed for {linkedin_url}: {str(e)}")
            return {
                "verified": False,
                "error": str(e),
                "profile_data": None
            }
    
    def _extract_profile_id(self, linkedin_url: str) -> Optional[str]:
        """Extract profile ID from LinkedIn URL"""
        if not linkedin_url:
            return None
        
        # Extract profile ID from URL like https://linkedin.com/in/john-doe
        parts = linkedin_url.strip('/').split('/')
        if 'in' in parts:
            in_index = parts.index('in')
            if in_index + 1 < len(parts):
                return parts[in_index + 1]
        
        return None
    
    async def _mock_profile_verification(self, profile_id: str) -> Dict[str, Any]:
        """Mock profile verification by profile ID"""
        await asyncio.sleep(0.3)
        
        # Mock successful verification for demonstration
        profile_data = {
            "profile_id": profile_id,
            "name": profile_id.replace('-', ' ').title(),
            "current_position": "Software Engineer",
            "company": "Tech Company",
            "industry": "Technology",
            "location": "San Francisco, CA",
            "connections": 1000,
            "profile_active": True
        }
        
        return {
            "verified": True,
            "confidence_score": 0.9,
            "profile_data": profile_data,
            "verification_method": "profile_lookup"
        }
    
    async def batch_verify(self, contacts: list) -> Dict[str, Dict[str, Any]]:
        """Verify multiple contacts in batch"""
        results = {}
        
        for contact in contacts:
            contact_id = contact.get('id') or contact.get('email')
            
            # Try URL verification first if available
            if contact.get('linkedin_url'):
                result = await self.verify_by_url(contact['linkedin_url'])
            else:
                # Fall back to email verification
                result = await self.verify_profile(
                    email=contact['email'],
                    name=f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip(),
                    company=contact.get('company')
                )
            
            results[contact_id] = result
            
            # Small delay between requests to be respectful
            await asyncio.sleep(0.1)
        
        return results