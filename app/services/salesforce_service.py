from typing import Optional, Dict, Any, List
from simple_salesforce import Salesforce
from loguru import logger
from app.core.config import settings


class SalesforceService:
    """Salesforce API integration for contact verification and deduplication"""
    
    def __init__(self):
        self.username = settings.salesforce_username
        self.password = settings.salesforce_password
        self.security_token = settings.salesforce_security_token
        self.domain = settings.salesforce_domain
        self.sf_client = None
    
    async def connect(self) -> bool:
        """Establish connection to Salesforce"""
        try:
            if not all([self.username, self.password, self.security_token]):
                logger.warning("Salesforce credentials not configured")
                return False
            
            self.sf_client = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
                domain=self.domain
            )
            
            logger.info("Successfully connected to Salesforce")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {str(e)}")
            return False
    
    async def verify_contact(self, email: str, phone: str = None) -> Dict[str, Any]:
        """Verify if contact exists in Salesforce"""
        try:
            if not self.sf_client:
                connected = await self.connect()
                if not connected:
                    return {
                        "verified": False,
                        "error": "Salesforce connection failed",
                        "contact_data": None,
                        "is_duplicate": False
                    }
            
            # Search for contact by email
            contact_data = await self._search_contact_by_email(email)
            
            if not contact_data and phone:
                # Try searching by phone if email search fails
                contact_data = await self._search_contact_by_phone(phone)
            
            if contact_data:
                return {
                    "verified": True,
                    "contact_data": contact_data,
                    "is_duplicate": True,
                    "match_type": "existing_contact"
                }
            
            # Check leads table as well
            lead_data = await self._search_lead_by_email(email)
            if lead_data:
                return {
                    "verified": True,
                    "contact_data": lead_data,
                    "is_duplicate": True,
                    "match_type": "existing_lead"
                }
            
            return {
                "verified": False,
                "contact_data": None,
                "is_duplicate": False,
                "match_type": "new_contact"
            }
            
        except Exception as e:
            logger.error(f"Salesforce verification failed for {email}: {str(e)}")
            return {
                "verified": False,
                "error": str(e),
                "contact_data": None,
                "is_duplicate": False
            }
    
    async def _search_contact_by_email(self, email: str) -> Optional[Dict]:
        """Search for contact by email in Salesforce"""
        try:
            query = f"SELECT Id, FirstName, LastName, Email, Phone, Account.Name, Title FROM Contact WHERE Email = '{email}' LIMIT 1"
            result = self.sf_client.query(query)
            
            if result['records']:
                contact = result['records'][0]
                return {
                    "id": contact['Id'],
                    "first_name": contact.get('FirstName'),
                    "last_name": contact.get('LastName'),
                    "email": contact.get('Email'),
                    "phone": contact.get('Phone'),
                    "company": contact.get('Account', {}).get('Name') if contact.get('Account') else None,
                    "title": contact.get('Title'),
                    "object_type": "Contact"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching contact by email: {str(e)}")
            return None
    
    async def _search_contact_by_phone(self, phone: str) -> Optional[Dict]:
        """Search for contact by phone in Salesforce"""
        try:
            # Clean phone number for search
            clean_phone = ''.join(filter(str.isdigit, phone))
            if len(clean_phone) < 10:
                return None
            
            query = f"SELECT Id, FirstName, LastName, Email, Phone, Account.Name, Title FROM Contact WHERE Phone LIKE '%{clean_phone[-10:]}%' LIMIT 1"
            result = self.sf_client.query(query)
            
            if result['records']:
                contact = result['records'][0]
                return {
                    "id": contact['Id'],
                    "first_name": contact.get('FirstName'),
                    "last_name": contact.get('LastName'),
                    "email": contact.get('Email'),
                    "phone": contact.get('Phone'),
                    "company": contact.get('Account', {}).get('Name') if contact.get('Account') else None,
                    "title": contact.get('Title'),
                    "object_type": "Contact"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching contact by phone: {str(e)}")
            return None
    
    async def _search_lead_by_email(self, email: str) -> Optional[Dict]:
        """Search for lead by email in Salesforce"""
        try:
            query = f"SELECT Id, FirstName, LastName, Email, Phone, Company, Title, Status FROM Lead WHERE Email = '{email}' LIMIT 1"
            result = self.sf_client.query(query)
            
            if result['records']:
                lead = result['records'][0]
                return {
                    "id": lead['Id'],
                    "first_name": lead.get('FirstName'),
                    "last_name": lead.get('LastName'),
                    "email": lead.get('Email'),
                    "phone": lead.get('Phone'),
                    "company": lead.get('Company'),
                    "title": lead.get('Title'),
                    "status": lead.get('Status'),
                    "object_type": "Lead"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching lead by email: {str(e)}")
            return None
    
    async def batch_verify(self, contacts: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """Verify multiple contacts against Salesforce"""
        results = {}
        
        if not self.sf_client:
            connected = await self.connect()
            if not connected:
                return {contact.get('email', str(i)): {
                    "verified": False,
                    "error": "Salesforce connection failed"
                } for i, contact in enumerate(contacts)}
        
        for contact in contacts:
            email = contact.get('email')
            phone = contact.get('phone')
            
            if email:
                result = await self.verify_contact(email, phone)
                results[email] = result
        
        return results
    
    async def get_account_info(self, company_name: str) -> Optional[Dict]:
        """Get account information by company name"""
        try:
            if not self.sf_client:
                await self.connect()
            
            query = f"SELECT Id, Name, Website, Industry, Phone FROM Account WHERE Name LIKE '%{company_name}%' LIMIT 1"
            result = self.sf_client.query(query)
            
            if result['records']:
                account = result['records'][0]
                return {
                    "id": account['Id'],
                    "name": account.get('Name'),
                    "website": account.get('Website'),
                    "industry": account.get('Industry'),
                    "phone": account.get('Phone')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    async def create_lead(self, contact_data: Dict) -> Optional[str]:
        """Create a new lead in Salesforce"""
        try:
            if not self.sf_client:
                await self.connect()
            
            lead_data = {
                'FirstName': contact_data.get('first_name'),
                'LastName': contact_data.get('last_name') or 'Unknown',
                'Email': contact_data.get('email'),
                'Phone': contact_data.get('phone'),
                'Company': contact_data.get('company') or 'Unknown',
                'Title': contact_data.get('job_title'),
                'LeadSource': 'AI Verification System',
                'Status': 'New'
            }
            
            # Remove None values
            lead_data = {k: v for k, v in lead_data.items() if v is not None}
            
            result = self.sf_client.Lead.create(lead_data)
            
            if result.get('success'):
                logger.info(f"Created lead in Salesforce: {result['id']}")
                return result['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating lead: {str(e)}")
            return None