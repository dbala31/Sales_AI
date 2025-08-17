import pandas as pd
from typing import Dict, List, Any, Optional
from loguru import logger
import os
from fuzzywuzzy import fuzz
import re


class MockSalesforceService:
    """Mock Salesforce service that uses CSV data instead of API"""
    
    def __init__(self, mock_data_path: str = "data/mock_salesforce_contacts.csv"):
        self.mock_data_path = mock_data_path
        self.contacts_df = None
        self.leads_df = None
        self.accounts_df = None
        self.load_mock_data()
    
    def load_mock_data(self):
        """Load mock Salesforce data from CSV files"""
        try:
            # Load contacts data
            if os.path.exists(self.mock_data_path):
                self.contacts_df = pd.read_csv(self.mock_data_path)
                logger.info(f"Loaded {len(self.contacts_df)} mock Salesforce contacts")
            else:
                # Create sample data if file doesn't exist
                self.contacts_df = self._create_sample_contacts()
                logger.info("Created sample Salesforce contacts data")
            
            # Normalize column names
            self.contacts_df.columns = [col.lower().replace(' ', '_') for col in self.contacts_df.columns]
            
            # Create sample leads and accounts data
            self.leads_df = self._create_sample_leads()
            self.accounts_df = self._create_sample_accounts()
            
        except Exception as e:
            logger.error(f"Error loading mock Salesforce data: {str(e)}")
            self.contacts_df = self._create_sample_contacts()
            self.leads_df = self._create_sample_leads()
            self.accounts_df = self._create_sample_accounts()
    
    def _create_sample_contacts(self) -> pd.DataFrame:
        """Create sample contacts data"""
        sample_data = [
            {
                'id': 'CONTACT_001',
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'john.smith@techcorp.com',
                'phone': '+1-555-0123',
                'company': 'TechCorp Inc',
                'title': 'Software Engineer',
                'account_name': 'TechCorp Inc'
            },
            {
                'id': 'CONTACT_002',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@innovate.com',
                'phone': '+1-555-0124',
                'company': 'Innovate Solutions',
                'title': 'Product Manager',
                'account_name': 'Innovate Solutions'
            },
            {
                'id': 'CONTACT_003',
                'first_name': 'Mike',
                'last_name': 'Davis',
                'email': 'mike.davis@startupco.com',
                'phone': '+1-555-0125',
                'company': 'StartupCo',
                'title': 'CTO',
                'account_name': 'StartupCo'
            }
        ]
        return pd.DataFrame(sample_data)
    
    def _create_sample_leads(self) -> pd.DataFrame:
        """Create sample leads data"""
        sample_data = [
            {
                'id': 'LEAD_001',
                'first_name': 'Emily',
                'last_name': 'Chen',
                'email': 'emily.chen@futuretech.com',
                'phone': '+1-555-0126',
                'company': 'FutureTech',
                'title': 'Director of Engineering',
                'status': 'New'
            },
            {
                'id': 'LEAD_002',
                'first_name': 'David',
                'last_name': 'Wilson',
                'email': 'david.wilson@cloudnext.com',
                'phone': '+1-555-0127',
                'company': 'CloudNext',
                'title': 'VP Sales',
                'status': 'Qualified'
            }
        ]
        return pd.DataFrame(sample_data)
    
    def _create_sample_accounts(self) -> pd.DataFrame:
        """Create sample accounts data"""
        sample_data = [
            {
                'id': 'ACCOUNT_001',
                'name': 'TechCorp Inc',
                'website': 'techcorp.com',
                'industry': 'Technology',
                'phone': '+1-555-1000'
            },
            {
                'id': 'ACCOUNT_002',
                'name': 'Innovate Solutions',
                'website': 'innovate.com',
                'industry': 'Software',
                'phone': '+1-555-2000'
            }
        ]
        return pd.DataFrame(sample_data)
    
    async def connect(self) -> bool:
        """Mock connection - always returns True"""
        logger.info("Mock Salesforce connection established")
        return True
    
    async def verify_contact(self, email: str, phone: str = None) -> Dict[str, Any]:
        """Verify if contact exists in mock Salesforce data"""
        try:
            result = {
                "verified": False,
                "contact_data": None,
                "is_duplicate": False,
                "match_type": "new_contact"
            }
            
            # Search contacts by email
            contact_match = await self._search_contact_by_email(email)
            if contact_match:
                result.update({
                    "verified": True,
                    "contact_data": contact_match,
                    "is_duplicate": True,
                    "match_type": "existing_contact"
                })
                return result
            
            # Search by phone if email search fails
            if phone:
                contact_match = await self._search_contact_by_phone(phone)
                if contact_match:
                    result.update({
                        "verified": True,
                        "contact_data": contact_match,
                        "is_duplicate": True,
                        "match_type": "existing_contact_phone_match"
                    })
                    return result
            
            # Search leads
            lead_match = await self._search_lead_by_email(email)
            if lead_match:
                result.update({
                    "verified": True,
                    "contact_data": lead_match,
                    "is_duplicate": True,
                    "match_type": "existing_lead"
                })
                return result
            
            return result
            
        except Exception as e:
            logger.error(f"Mock Salesforce verification failed for {email}: {str(e)}")
            return {
                "verified": False,
                "error": str(e),
                "contact_data": None,
                "is_duplicate": False
            }
    
    async def _search_contact_by_email(self, email: str) -> Optional[Dict]:
        """Search for contact by email in mock data"""
        try:
            matches = self.contacts_df[self.contacts_df['email'].str.lower() == email.lower()]
            
            if not matches.empty:
                contact = matches.iloc[0]
                return {
                    "id": contact['id'],
                    "first_name": contact.get('first_name'),
                    "last_name": contact.get('last_name'),
                    "email": contact.get('email'),
                    "phone": contact.get('phone'),
                    "company": contact.get('account_name') or contact.get('company'),
                    "title": contact.get('title'),
                    "object_type": "Contact"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching contact by email: {str(e)}")
            return None
    
    async def _search_contact_by_phone(self, phone: str) -> Optional[Dict]:
        """Search for contact by phone in mock data"""
        try:
            # Clean phone number for search
            clean_phone = re.sub(r'[^\d]', '', phone)
            if len(clean_phone) < 10:
                return None
            
            # Search for phone number (last 10 digits)
            phone_pattern = clean_phone[-10:]
            
            for _, contact in self.contacts_df.iterrows():
                contact_phone = str(contact.get('phone', ''))
                contact_clean = re.sub(r'[^\d]', '', contact_phone)
                
                if phone_pattern in contact_clean:
                    return {
                        "id": contact['id'],
                        "first_name": contact.get('first_name'),
                        "last_name": contact.get('last_name'),
                        "email": contact.get('email'),
                        "phone": contact.get('phone'),
                        "company": contact.get('account_name') or contact.get('company'),
                        "title": contact.get('title'),
                        "object_type": "Contact"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching contact by phone: {str(e)}")
            return None
    
    async def _search_lead_by_email(self, email: str) -> Optional[Dict]:
        """Search for lead by email in mock data"""
        try:
            matches = self.leads_df[self.leads_df['email'].str.lower() == email.lower()]
            
            if not matches.empty:
                lead = matches.iloc[0]
                return {
                    "id": lead['id'],
                    "first_name": lead.get('first_name'),
                    "last_name": lead.get('last_name'),
                    "email": lead.get('email'),
                    "phone": lead.get('phone'),
                    "company": lead.get('company'),
                    "title": lead.get('title'),
                    "status": lead.get('status'),
                    "object_type": "Lead"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching lead by email: {str(e)}")
            return None
    
    async def batch_verify(self, contacts: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """Verify multiple contacts against mock Salesforce data"""
        results = {}
        
        for contact in contacts:
            email = contact.get('email')
            phone = contact.get('phone')
            
            if email:
                result = await self.verify_contact(email, phone)
                results[email] = result
        
        return results
    
    async def get_account_info(self, company_name: str) -> Optional[Dict]:
        """Get account information by company name from mock data"""
        try:
            # Fuzzy match company name
            best_match = None
            best_score = 0
            
            for _, account in self.accounts_df.iterrows():
                account_name = str(account.get('name', ''))
                score = fuzz.ratio(company_name.lower(), account_name.lower())
                
                if score > best_score and score > 70:  # 70% similarity threshold
                    best_score = score
                    best_match = account
            
            if best_match is not None:
                return {
                    "id": best_match['id'],
                    "name": best_match.get('name'),
                    "website": best_match.get('website'),
                    "industry": best_match.get('industry'),
                    "phone": best_match.get('phone')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    async def create_lead(self, contact_data: Dict) -> Optional[str]:
        """Mock creating a new lead - just logs the action"""
        try:
            lead_id = f"MOCK_LEAD_{len(self.leads_df) + 1:03d}"
            
            new_lead = {
                'id': lead_id,
                'first_name': contact_data.get('first_name'),
                'last_name': contact_data.get('last_name') or 'Unknown',
                'email': contact_data.get('email'),
                'phone': contact_data.get('phone'),
                'company': contact_data.get('company') or 'Unknown',
                'title': contact_data.get('job_title'),
                'status': 'New'
            }
            
            # Add to mock leads dataframe
            new_lead_df = pd.DataFrame([new_lead])
            self.leads_df = pd.concat([self.leads_df, new_lead_df], ignore_index=True)
            
            logger.info(f"Mock lead created: {lead_id} for {contact_data.get('email')}")
            return lead_id
            
        except Exception as e:
            logger.error(f"Error creating mock lead: {str(e)}")
            return None
    
    def load_custom_data(self, csv_path: str):
        """Load custom CSV data for testing"""
        try:
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                # Normalize column names
                df.columns = [col.lower().replace(' ', '_') for col in df.columns]
                
                # Determine data type based on columns
                if 'account_name' in df.columns or 'company' in df.columns:
                    self.contacts_df = df
                    logger.info(f"Loaded {len(df)} custom contacts from {csv_path}")
                elif 'status' in df.columns:
                    self.leads_df = df
                    logger.info(f"Loaded {len(df)} custom leads from {csv_path}")
                else:
                    # Default to contacts
                    self.contacts_df = df
                    logger.info(f"Loaded {len(df)} custom data as contacts from {csv_path}")
            else:
                logger.warning(f"Custom data file not found: {csv_path}")
                
        except Exception as e:
            logger.error(f"Error loading custom data from {csv_path}: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about mock data"""
        return {
            "contacts_count": len(self.contacts_df) if self.contacts_df is not None else 0,
            "leads_count": len(self.leads_df) if self.leads_df is not None else 0,
            "accounts_count": len(self.accounts_df) if self.accounts_df is not None else 0,
            "data_source": "mock_csv_data"
        }