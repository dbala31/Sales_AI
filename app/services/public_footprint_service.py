import asyncio
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import Dict, List, Any, Optional
from loguru import logger
import time


class PublicFootprintService:
    """Public footprint checking service using free methods only"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1  # Minimum 1 second between requests
    
    async def check_public_footprint(self, email: str, first_name: str = None, 
                                   last_name: str = None, company: str = None) -> Dict[str, Any]:
        """Check public footprint for email/person across various sources"""
        
        result = {
            "email_found": False,
            "person_found": False,
            "confidence_score": 0.0,
            "sources": [],
            "evidence": []
        }
        
        if not email and not (first_name and last_name):
            result["error"] = "Need either email or full name"
            return result
        
        try:
            # Check company domain for email/person
            if company:
                domain_result = await self._check_company_domain(
                    email, first_name, last_name, company
                )
                if domain_result["found"]:
                    result["email_found"] = domain_result["email_found"]
                    result["person_found"] = domain_result["person_found"]
                    result["sources"].append("company_domain")
                    result["evidence"].extend(domain_result["evidence"])
            
            # Check search engines (limited free approach)
            search_result = await self._check_search_engines(
                email, first_name, last_name, company
            )
            if search_result["found"]:
                result["email_found"] = result["email_found"] or search_result["email_found"]
                result["person_found"] = result["person_found"] or search_result["person_found"]
                result["sources"].append("search_engines")
                result["evidence"].extend(search_result["evidence"])
            
            # Check social media presence (free methods only)
            social_result = await self._check_social_media_presence(
                email, first_name, last_name, company
            )
            if social_result["found"]:
                result["person_found"] = True
                result["sources"].append("social_media")
                result["evidence"].extend(social_result["evidence"])
            
            # Calculate confidence score
            result["confidence_score"] = self._calculate_footprint_confidence(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Public footprint check failed: {str(e)}")
            result["error"] = str(e)
            return result
    
    async def _check_company_domain(self, email: str, first_name: str, 
                                  last_name: str, company: str) -> Dict[str, Any]:
        """Check company domain for email/person mentions"""
        
        result = {
            "found": False,
            "email_found": False,
            "person_found": False,
            "evidence": []
        }
        
        try:
            # Extract/guess company domain
            company_domain = self._extract_company_domain(company, email)
            if not company_domain:
                return result
            
            # Rate limiting
            await self._rate_limit()
            
            # Search company domain
            base_url = f"https://{company_domain}"
            
            # Try main page first
            try:
                response = self.session.get(base_url, timeout=10)
                if response.status_code == 200:
                    content = response.text.lower()
                    
                    # Check for email
                    if email and email.lower() in content:
                        result["email_found"] = True
                        result["found"] = True
                        result["evidence"].append({
                            "type": "email_on_company_site",
                            "url": base_url,
                            "method": "direct_page_search"
                        })
                    
                    # Check for person name
                    if first_name and last_name:
                        full_name = f"{first_name} {last_name}".lower()
                        if full_name in content:
                            result["person_found"] = True
                            result["found"] = True
                            result["evidence"].append({
                                "type": "name_on_company_site",
                                "url": base_url,
                                "name": full_name,
                                "method": "direct_page_search"
                            })
            
            except Exception as e:
                logger.warning(f"Error checking company domain {company_domain}: {str(e)}")
            
            # Try common pages (team, about, contact)
            common_pages = ['/team', '/about', '/contact', '/staff', '/people']
            for page in common_pages:
                try:
                    await self._rate_limit()
                    
                    page_url = f"{base_url}{page}"
                    response = self.session.get(page_url, timeout=10)
                    
                    if response.status_code == 200:
                        content = response.text.lower()
                        
                        # Check for email
                        if email and email.lower() in content:
                            result["email_found"] = True
                            result["found"] = True
                            result["evidence"].append({
                                "type": "email_on_company_page",
                                "url": page_url,
                                "method": "team_page_search"
                            })
                        
                        # Check for person name
                        if first_name and last_name:
                            full_name = f"{first_name} {last_name}".lower()
                            if full_name in content:
                                result["person_found"] = True
                                result["found"] = True
                                result["evidence"].append({
                                    "type": "name_on_company_page",
                                    "url": page_url,
                                    "name": full_name,
                                    "method": "team_page_search"
                                })
                
                except Exception as e:
                    continue  # Skip failed pages
            
            return result
            
        except Exception as e:
            logger.warning(f"Company domain check failed: {str(e)}")
            return result
    
    async def _check_search_engines(self, email: str, first_name: str, 
                                  last_name: str, company: str) -> Dict[str, Any]:
        """Check search engines for email/person (free methods)"""
        
        result = {
            "found": False,
            "email_found": False,
            "person_found": False,
            "evidence": []
        }
        
        try:
            # Build search queries
            queries = []
            
            if email:
                queries.append(f'"{email}"')
            
            if first_name and last_name:
                queries.append(f'"{first_name} {last_name}"')
                
                if company:
                    queries.append(f'"{first_name} {last_name}" "{company}"')
            
            # For each query, we would normally search
            # However, search engines block automated queries
            # This is a placeholder for the concept
            
            # Note: In production, you would need to:
            # 1. Use official search APIs (which cost money)
            # 2. Use alternative search engines that allow automation
            # 3. Implement CAPTCHA solving (complex)
            # 4. Use proxy rotation (against ToS)
            
            # For now, we'll return a placeholder result
            result["found"] = False
            result["evidence"].append({
                "type": "search_engine_check",
                "status": "not_implemented",
                "note": "Search engine verification requires API access or complex automation",
                "queries_that_would_be_searched": queries
            })
            
            return result
            
        except Exception as e:
            logger.warning(f"Search engine check failed: {str(e)}")
            return result
    
    async def _check_social_media_presence(self, email: str, first_name: str,
                                         last_name: str, company: str) -> Dict[str, Any]:
        """Check social media presence (free methods only)"""
        
        result = {
            "found": False,
            "evidence": []
        }
        
        try:
            # Check if common social media profile URLs are accessible
            # This is a basic check - not scraping content due to ToS
            
            if first_name and last_name:
                # Generate potential LinkedIn profile URLs
                name_variants = [
                    f"{first_name.lower()}-{last_name.lower()}",
                    f"{first_name.lower()}{last_name.lower()}",
                    f"{first_name[0].lower()}{last_name.lower()}" if first_name else ""
                ]
                
                # Check if LinkedIn profiles exist (just HEAD request to check existence)
                for variant in name_variants:
                    if not variant:
                        continue
                    
                    try:
                        await self._rate_limit()
                        
                        linkedin_url = f"https://linkedin.com/in/{variant}"
                        response = self.session.head(linkedin_url, timeout=5)
                        
                        # If profile exists (200) and it's not a generic error page
                        if response.status_code == 200:
                            result["found"] = True
                            result["evidence"].append({
                                "type": "linkedin_profile_exists",
                                "url": linkedin_url,
                                "method": "profile_url_check"
                            })
                            break  # Found one, that's enough
                    
                    except Exception as e:
                        continue  # Try next variant
            
            return result
            
        except Exception as e:
            logger.warning(f"Social media check failed: {str(e)}")
            return result
    
    def _extract_company_domain(self, company: str, email: str = None) -> Optional[str]:
        """Extract company domain from company name or email"""
        
        # If email is provided, try to use its domain
        if email and '@' in email:
            email_domain = email.split('@')[1].lower()
            
            # Check if it's likely a company domain (not gmail, yahoo, etc.)
            free_domains = {
                'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                'aol.com', 'icloud.com', 'live.com', 'msn.com'
            }
            
            if email_domain not in free_domains:
                return email_domain
        
        # Try to guess domain from company name
        if company:
            # Clean company name
            company_clean = re.sub(r'[^a-zA-Z0-9\s]', '', company.lower())
            company_clean = re.sub(r'\b(inc|llc|corp|company|ltd|limited|co)\b', '', company_clean)
            company_clean = company_clean.strip().replace(' ', '')
            
            if company_clean:
                return f"{company_clean}.com"
        
        return None
    
    def _calculate_footprint_confidence(self, result: Dict) -> float:
        """Calculate confidence score based on footprint evidence"""
        score = 0.0
        
        # Email found on company domain
        if result["email_found"]:
            score += 0.5
        
        # Person found on company domain
        if result["person_found"]:
            score += 0.3
        
        # Multiple sources
        if len(result["sources"]) > 1:
            score += 0.2
        
        # Evidence quality
        high_quality_evidence = sum(
            1 for evidence in result["evidence"] 
            if evidence.get("type") in ["email_on_company_site", "name_on_company_page"]
        )
        
        score += min(0.3, high_quality_evidence * 0.1)
        
        return min(score, 1.0)
    
    async def _rate_limit(self):
        """Simple rate limiting to be respectful"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    async def batch_check_footprint(self, contacts: List[Dict]) -> Dict[str, Dict]:
        """Check public footprint for multiple contacts"""
        results = {}
        
        for contact in contacts:
            contact_id = contact.get('email', str(id(contact)))
            
            try:
                result = await self.check_public_footprint(
                    email=contact.get('email'),
                    first_name=contact.get('first_name'),
                    last_name=contact.get('last_name'),
                    company=contact.get('company')
                )
                
                results[contact_id] = result
                
                # Rate limiting between contacts
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Footprint check failed for {contact_id}: {str(e)}")
                results[contact_id] = {
                    "email_found": False,
                    "person_found": False,
                    "error": str(e)
                }
        
        return results