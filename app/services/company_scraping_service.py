import asyncio
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional, Set
from loguru import logger
from fuzzywuzzy import fuzz
import tldextract


class CompanyScrapingService:
    """Company website scraping service for contact verification"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Common staff/team page patterns
        self.team_page_patterns = [
            '/team', '/about', '/people', '/staff', '/leadership', '/management',
            '/about-us', '/meet-the-team', '/our-team', '/employees', '/directory',
            '/founders', '/executives', '/board', '/advisory', '/company/team'
        ]
        
        # Common selectors for finding people on pages
        self.people_selectors = [
            '.team-member', '.staff-member', '.employee', '.person',
            '.bio', '.profile', '.team-bio', '.staff-bio',
            '[class*="team"]', '[class*="staff"]', '[class*="member"]',
            '[class*="employee"]', '[class*="person"]', '[class*="bio"]'
        ]
        
        # Name patterns to avoid false positives
        self.name_stopwords = {
            'team', 'staff', 'about', 'company', 'contact', 'home', 'page',
            'more', 'read', 'view', 'click', 'here', 'learn', 'see', 'meet'
        }
    
    async def verify_employment(self, first_name: str, last_name: str, 
                              company_domain: str, job_title: str = None) -> Dict[str, Any]:
        """Verify if person works at company by scraping company website"""
        
        result = {
            "employment_verified": False,
            "confidence_score": 0.0,
            "evidence": [],
            "pages_checked": [],
            "method": "website_scraping"
        }
        
        if not company_domain or not first_name or not last_name:
            result["error"] = "Missing required information"
            return result
        
        try:
            # Clean and normalize domain
            domain = self._normalize_domain(company_domain)
            if not domain:
                result["error"] = "Invalid domain"
                return result
            
            # Find team/about pages
            team_pages = await self._find_team_pages(domain)
            result["pages_checked"] = team_pages
            
            # Search for person on team pages
            for page_url in team_pages:
                try:
                    page_result = await self._search_person_on_page(
                        page_url, first_name, last_name, job_title
                    )
                    
                    if page_result["found"]:
                        result["employment_verified"] = True
                        result["confidence_score"] = page_result["confidence"]
                        result["evidence"].append({
                            "page": page_url,
                            "matches": page_result["matches"],
                            "context": page_result["context"]
                        })
                        
                        # If we find strong evidence, we can stop
                        if page_result["confidence"] > 0.8:
                            break
                    
                except Exception as e:
                    logger.warning(f"Error checking page {page_url}: {str(e)}")
                    continue
            
            # If not found on team pages, try general site search
            if not result["employment_verified"]:
                search_result = await self._search_site_for_person(
                    domain, first_name, last_name
                )
                if search_result["found"]:
                    result["employment_verified"] = True
                    result["confidence_score"] = search_result["confidence"]
                    result["evidence"].append(search_result["evidence"])
            
            return result
            
        except Exception as e:
            logger.error(f"Employment verification failed for {first_name} {last_name} at {company_domain}: {str(e)}")
            result["error"] = str(e)
            return result
    
    def _normalize_domain(self, domain: str) -> Optional[str]:
        """Normalize domain URL"""
        if not domain:
            return None
        
        # Remove protocol and www
        domain = re.sub(r'^https?://', '', domain.lower())
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split('/')[0]  # Remove path
        
        # Validate domain format
        if '.' not in domain or len(domain) < 4:
            return None
        
        return domain
    
    async def _find_team_pages(self, domain: str) -> List[str]:
        """Find team/about pages on company website"""
        team_pages = []
        base_url = f"https://{domain}"
        
        # First try to get main page to find links
        try:
            response = self.session.get(base_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for team page links
                for link in soup.find_all('a', href=True):
                    href = link['href'].lower()
                    if any(pattern in href for pattern in self.team_page_patterns):
                        full_url = urljoin(base_url, link['href'])
                        if full_url not in team_pages:
                            team_pages.append(full_url)
        
        except Exception as e:
            logger.warning(f"Could not fetch main page for {domain}: {str(e)}")
        
        # Also try direct common URLs
        for pattern in self.team_page_patterns[:10]:  # Limit to avoid too many requests
            url = f"{base_url}{pattern}"
            if url not in team_pages:
                team_pages.append(url)
        
        return team_pages
    
    async def _search_person_on_page(self, page_url: str, first_name: str, 
                                   last_name: str, job_title: str = None) -> Dict[str, Any]:
        """Search for a specific person on a webpage"""
        
        result = {
            "found": False,
            "confidence": 0.0,
            "matches": [],
            "context": ""
        }
        
        try:
            response = self.session.get(page_url, timeout=10)
            if response.status_code != 200:
                return result
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Search for full name
            full_name = f"{first_name} {last_name}".lower()
            name_variations = [
                full_name,
                f"{last_name}, {first_name}".lower(),
                f"{first_name.split()[0]} {last_name}".lower() if ' ' in first_name else full_name
            ]
            
            # Check for name matches
            name_matches = []
            for name_var in name_variations:
                if name_var in page_text:
                    name_matches.append(name_var)
                    result["found"] = True
            
            if name_matches:
                result["matches"].extend(name_matches)
                result["confidence"] = 0.6  # Base confidence for name match
                
                # Look for additional context (job title, department, etc.)
                if job_title:
                    title_words = job_title.lower().split()
                    title_matches = sum(1 for word in title_words if word in page_text)
                    if title_matches > 0:
                        result["confidence"] += 0.2 * (title_matches / len(title_words))
                
                # Check if it's in a team/staff context
                team_context_keywords = [
                    'team', 'staff', 'employee', 'member', 'leadership',
                    'management', 'director', 'manager', 'executive'
                ]
                
                # Find context around the name
                for name in name_matches:
                    name_index = page_text.find(name)
                    if name_index >= 0:
                        context_start = max(0, name_index - 200)
                        context_end = min(len(page_text), name_index + 200)
                        context = page_text[context_start:context_end]
                        result["context"] = context
                        
                        # Check for team context
                        context_matches = sum(1 for keyword in team_context_keywords 
                                           if keyword in context)
                        if context_matches > 0:
                            result["confidence"] += 0.2
                        
                        break
                
                # Cap confidence at 1.0
                result["confidence"] = min(result["confidence"], 1.0)
            
            return result
            
        except Exception as e:
            logger.warning(f"Error searching page {page_url}: {str(e)}")
            return result
    
    async def _search_site_for_person(self, domain: str, first_name: str, 
                                    last_name: str) -> Dict[str, Any]:
        """Search entire site for person using site search or Google"""
        
        result = {
            "found": False,
            "confidence": 0.0,
            "evidence": {}
        }
        
        try:
            # Try site-specific search using Google
            search_query = f"site:{domain} \"{first_name} {last_name}\""
            
            # Use requests to search (this is a basic implementation)
            # In production, you might want to use a proper search API
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            # Note: This is a simplified approach. Google blocks automated searches.
            # For production, consider using official APIs or other search engines.
            
            # For now, return a placeholder result
            result["found"] = False
            result["confidence"] = 0.0
            result["evidence"] = {
                "method": "google_site_search",
                "query": search_query,
                "note": "Search engine verification would require proper API integration"
            }
            
            return result
            
        except Exception as e:
            logger.warning(f"Site search failed for {first_name} {last_name} at {domain}: {str(e)}")
            return result
    
    async def verify_company_domain(self, company_name: str, 
                                  provided_domain: str = None) -> Dict[str, Any]:
        """Verify and find company's primary domain"""
        
        result = {
            "verified": False,
            "primary_domain": None,
            "alternative_domains": [],
            "confidence": 0.0
        }
        
        if not company_name:
            return result
        
        try:
            # If domain is provided, verify it matches company
            if provided_domain:
                domain_result = await self._verify_domain_matches_company(
                    provided_domain, company_name
                )
                if domain_result["matches"]:
                    result["verified"] = True
                    result["primary_domain"] = provided_domain
                    result["confidence"] = domain_result["confidence"]
                    return result
            
            # Try to find company domain
            suggested_domains = self._generate_domain_suggestions(company_name)
            
            for domain in suggested_domains:
                try:
                    # Check if domain is accessible
                    response = self.session.head(f"https://{domain}", timeout=5)
                    if response.status_code == 200:
                        # Verify it's the right company
                        verification = await self._verify_domain_matches_company(
                            domain, company_name
                        )
                        if verification["matches"]:
                            result["verified"] = True
                            result["primary_domain"] = domain
                            result["confidence"] = verification["confidence"]
                            break
                        else:
                            result["alternative_domains"].append(domain)
                
                except:
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Domain verification failed for {company_name}: {str(e)}")
            return result
    
    def _generate_domain_suggestions(self, company_name: str) -> List[str]:
        """Generate possible domain names for company"""
        suggestions = []
        
        # Clean company name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name.lower())
        clean_name = re.sub(r'\b(inc|llc|corp|company|ltd|limited|co)\b', '', clean_name)
        clean_name = clean_name.strip()
        
        # Generate variations
        name_parts = clean_name.split()
        if name_parts:
            # Single word or joined
            single_word = ''.join(name_parts)
            suggestions.extend([
                f"{single_word}.com",
                f"{single_word}.net",
                f"{single_word}.org"
            ])
            
            # With hyphens
            if len(name_parts) > 1:
                hyphenated = '-'.join(name_parts)
                suggestions.extend([
                    f"{hyphenated}.com",
                    f"{hyphenated}.net"
                ])
            
            # First word only
            suggestions.extend([
                f"{name_parts[0]}.com",
                f"{name_parts[0]}.net"
            ])
        
        return suggestions[:10]  # Limit suggestions
    
    async def _verify_domain_matches_company(self, domain: str, 
                                           company_name: str) -> Dict[str, Any]:
        """Verify that domain belongs to the specified company"""
        
        result = {
            "matches": False,
            "confidence": 0.0,
            "evidence": []
        }
        
        try:
            url = f"https://{domain}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                page_text = soup.get_text().lower()
                
                # Clean company name for matching
                clean_company = re.sub(r'[^a-zA-Z0-9\s]', '', company_name.lower())
                company_words = clean_company.split()
                
                # Check for company name mentions
                matches = 0
                total_words = len(company_words)
                
                for word in company_words:
                    if len(word) > 2 and word in page_text:  # Skip very short words
                        matches += 1
                
                if matches > 0:
                    confidence = matches / total_words
                    if confidence >= 0.6:  # At least 60% of company name words found
                        result["matches"] = True
                        result["confidence"] = confidence
                        result["evidence"].append(f"Found {matches}/{total_words} company name words")
                
                # Check title tag
                title = soup.find('title')
                if title:
                    title_text = title.get_text().lower()
                    title_similarity = fuzz.partial_ratio(clean_company, title_text)
                    if title_similarity > 70:
                        result["matches"] = True
                        result["confidence"] = max(result["confidence"], title_similarity / 100)
                        result["evidence"].append(f"Company name in title (similarity: {title_similarity}%)")
            
            return result
            
        except Exception as e:
            logger.warning(f"Error verifying domain {domain} for company {company_name}: {str(e)}")
            return result
    
    async def batch_verify_employment(self, contacts: List[Dict]) -> Dict[str, Dict]:
        """Batch verify employment for multiple contacts"""
        results = {}
        
        for contact in contacts:
            contact_id = contact.get('email', str(id(contact)))
            
            try:
                result = await self.verify_employment(
                    first_name=contact.get('first_name', ''),
                    last_name=contact.get('last_name', ''),
                    company_domain=contact.get('company_domain') or contact.get('company'),
                    job_title=contact.get('job_title')
                )
                
                results[contact_id] = result
                
                # Rate limiting - be respectful to websites
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Employment verification failed for {contact_id}: {str(e)}")
                results[contact_id] = {
                    "employment_verified": False,
                    "error": str(e)
                }
        
        return results