import re
import asyncio
import smtplib
import socket
import dns.resolver
import tldextract
from email.utils import parseaddr
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
import aiosmtplib
from email.mime.text import MIMEText


class EmailVerificationService:
    """Free email verification pipeline without paid APIs"""
    
    def __init__(self):
        # RFC 5322 compliant email regex
        self.email_regex = re.compile(
            r'^[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*@'
            r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$'
        )
        
        # Load disposable email domains
        self.disposable_domains = self._load_disposable_domains()
        self.role_emails = self._load_role_emails()
        
        # Common email patterns for generation
        self.email_patterns = [
            "{first}.{last}@{domain}",
            "{first}{last}@{domain}",
            "{first_initial}{last}@{domain}",
            "{first}{last_initial}@{domain}",
            "{first_initial}.{last}@{domain}",
            "{first}.{last_initial}@{domain}",
            "{last}.{first}@{domain}",
            "{last}{first}@{domain}",
        ]
    
    def _load_disposable_domains(self) -> set:
        """Load list of disposable email domains"""
        # Common disposable email domains
        disposable_domains = {
            '10minutemail.com', '0-mail.com', '1-mail.com', '33mail.com',
            'dispostable.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', '10minutemail.net', 'temp-mail.org',
            'throwaway.email', 'yopmail.com', 'maildrop.cc',
            'sharklasers.com', 'grr.la', 'guerrillamailblock.com',
            'trashmail.com', 'spambog.com', 'tempail.com',
            'mohmal.com', 'emailondeck.com', 'jetable.org'
        }
        
        # You can extend this by fetching from public lists
        # e.g., https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains/master/disposable_email_blocklist.conf
        
        return disposable_domains
    
    def _load_role_emails(self) -> set:
        """Load list of role-based email prefixes"""
        return {
            'admin', 'administrator', 'support', 'help', 'info', 'contact',
            'sales', 'marketing', 'webmaster', 'postmaster', 'abuse',
            'security', 'legal', 'privacy', 'compliance', 'hr', 'recruiting',
            'careers', 'jobs', 'billing', 'accounting', 'finance', 'noreply',
            'no-reply', 'donotreply', 'mail', 'email', 'mail-daemon',
            'mailer-daemon', 'root', 'hostmaster', 'ftp', 'www', 'usenet',
            'news', 'operator', 'manager', 'service', 'orders'
        }
    
    async def verify_email_comprehensive(self, email: str, 
                                       first_name: str = None, 
                                       last_name: str = None,
                                       company: str = None,
                                       domain: str = None) -> Dict[str, Any]:
        """Comprehensive email verification pipeline"""
        
        result = {
            "email": email,
            "is_valid": False,
            "confidence_score": 0.0,
            "verification_stages": {},
            "issues": [],
            "suggested_emails": []
        }
        
        try:
            # Stage 1: Syntax Check (RFC 5322)
            syntax_result = self._check_syntax(email)
            result["verification_stages"]["syntax"] = syntax_result
            
            if not syntax_result["valid"]:
                result["issues"].extend(syntax_result["issues"])
                return result
            
            # Stage 2: Disposable/Role Email Filter
            filter_result = self._check_disposable_role(email)
            result["verification_stages"]["filter"] = filter_result
            
            if filter_result["is_disposable"] or filter_result["is_role"]:
                result["issues"].extend(filter_result["issues"])
                result["confidence_score"] = 0.2  # Very low confidence
                return result
            
            # Stage 3: Domain DNS Checks
            domain_result = await self._check_domain_dns(email)
            result["verification_stages"]["domain"] = domain_result
            
            if not domain_result["has_mx"]:
                result["issues"].append("Domain has no MX records")
                # Try to suggest alternatives if we have name/company info
                if first_name and last_name and (domain or company):
                    suggestions = await self._generate_email_suggestions(
                        first_name, last_name, domain or company
                    )
                    result["suggested_emails"] = suggestions
                return result
            
            # Stage 4: SMTP RCPT TO Check
            smtp_result = await self._check_smtp_deliverability(email)
            result["verification_stages"]["smtp"] = smtp_result
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(
                syntax_result, filter_result, domain_result, smtp_result
            )
            result["confidence_score"] = confidence
            result["is_valid"] = confidence >= 0.7
            
            return result
            
        except Exception as e:
            logger.error(f"Email verification failed for {email}: {str(e)}")
            result["issues"].append(f"Verification error: {str(e)}")
            return result
    
    def _check_syntax(self, email: str) -> Dict[str, Any]:
        """Check email syntax against RFC 5322"""
        result = {
            "valid": False,
            "issues": []
        }
        
        if not email:
            result["issues"].append("Email is empty")
            return result
        
        # Basic length check
        if len(email) > 254:
            result["issues"].append("Email too long (>254 characters)")
            return result
        
        # Parse email
        parsed_name, parsed_email = parseaddr(email)
        if parsed_email != email.lower():
            result["issues"].append("Email contains invalid characters")
            return result
        
        # Check with regex
        if not self.email_regex.match(email):
            result["issues"].append("Email format invalid (RFC 5322)")
            return result
        
        # Check local part length
        local_part = email.split('@')[0]
        if len(local_part) > 64:
            result["issues"].append("Local part too long (>64 characters)")
            return result
        
        result["valid"] = True
        return result
    
    def _check_disposable_role(self, email: str) -> Dict[str, Any]:
        """Check for disposable and role-based emails"""
        result = {
            "is_disposable": False,
            "is_role": False,
            "issues": []
        }
        
        local_part, domain = email.lower().split('@')
        
        # Check disposable domains
        if domain in self.disposable_domains:
            result["is_disposable"] = True
            result["issues"].append(f"Disposable email domain: {domain}")
        
        # Check role emails
        if local_part in self.role_emails:
            result["is_role"] = True
            result["issues"].append(f"Role-based email: {local_part}")
        
        return result
    
    async def _check_domain_dns(self, email: str) -> Dict[str, Any]:
        """Check domain DNS records"""
        result = {
            "domain": "",
            "has_a_record": False,
            "has_mx": False,
            "mx_records": [],
            "issues": []
        }
        
        try:
            domain = email.split('@')[1]
            result["domain"] = domain
            
            # Check A record
            try:
                a_records = dns.resolver.resolve(domain, 'A')
                result["has_a_record"] = len(a_records) > 0
            except:
                result["issues"].append("No A record found")
            
            # Check MX record
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                result["mx_records"] = [str(mx) for mx in mx_records]
                result["has_mx"] = len(mx_records) > 0
            except:
                result["issues"].append("No MX record found")
            
            return result
            
        except Exception as e:
            result["issues"].append(f"DNS lookup failed: {str(e)}")
            return result
    
    async def _check_smtp_deliverability(self, email: str) -> Dict[str, Any]:
        """Check SMTP deliverability with RCPT TO"""
        result = {
            "smtp_valid": False,
            "is_catch_all": False,
            "smtp_response": "",
            "issues": []
        }
        
        try:
            domain = email.split('@')[1]
            
            # Get MX record
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                mx_host = str(mx_records[0]).split()[-1].rstrip('.')
            except:
                result["issues"].append("No MX record for SMTP check")
                return result
            
            # SMTP handshake
            try:
                # Connect to SMTP server
                server = smtplib.SMTP(timeout=10)
                server.connect(mx_host, 25)
                server.helo('verification.test')
                
                # Try RCPT TO
                code, response = server.rcpt(email)
                result["smtp_response"] = response.decode() if isinstance(response, bytes) else str(response)
                
                if code == 250:
                    result["smtp_valid"] = True
                elif code in [550, 551, 553]:
                    result["issues"].append(f"Email rejected by server: {response}")
                elif code in [450, 451, 452]:
                    result["issues"].append(f"Temporary delivery issue: {response}")
                else:
                    result["issues"].append(f"Uncertain SMTP response: {code} {response}")
                
                # Test for catch-all by trying a random email
                random_email = f"nonexistent{asyncio.get_event_loop().time()}@{domain}"
                code_random, _ = server.rcpt(random_email)
                if code_random == 250:
                    result["is_catch_all"] = True
                    result["issues"].append("Domain appears to be catch-all")
                
                server.quit()
                
            except Exception as smtp_e:
                result["issues"].append(f"SMTP connection failed: {str(smtp_e)}")
            
            return result
            
        except Exception as e:
            result["issues"].append(f"SMTP check failed: {str(e)}")
            return result
    
    def _calculate_confidence_score(self, syntax_result: Dict, 
                                  filter_result: Dict, 
                                  domain_result: Dict, 
                                  smtp_result: Dict) -> float:
        """Calculate overall confidence score"""
        score = 0.0
        
        # Syntax check (20%)
        if syntax_result["valid"]:
            score += 0.2
        
        # Filter check (20%)
        if not filter_result["is_disposable"] and not filter_result["is_role"]:
            score += 0.2
        
        # Domain DNS (30%)
        if domain_result["has_a_record"]:
            score += 0.1
        if domain_result["has_mx"]:
            score += 0.2
        
        # SMTP check (30%)
        if smtp_result["smtp_valid"]:
            score += 0.3
        elif smtp_result["is_catch_all"]:
            score += 0.15  # Lower confidence for catch-all
        
        return min(score, 1.0)
    
    async def _generate_email_suggestions(self, first_name: str, 
                                        last_name: str, 
                                        domain_or_company: str) -> List[str]:
        """Generate email suggestions based on name and domain/company"""
        suggestions = []
        
        # Clean inputs
        first = re.sub(r'[^a-zA-Z]', '', first_name.lower()) if first_name else ""
        last = re.sub(r'[^a-zA-Z]', '', last_name.lower()) if last_name else ""
        
        if not first or not last:
            return suggestions
        
        # Determine domain
        domain = self._extract_domain(domain_or_company)
        if not domain:
            return suggestions
        
        # Generate email patterns
        patterns_data = {
            "first": first,
            "last": last,
            "first_initial": first[0] if first else "",
            "last_initial": last[0] if last else "",
            "domain": domain
        }
        
        # Generate candidates
        candidates = []
        for pattern in self.email_patterns:
            try:
                email = pattern.format(**patterns_data)
                if email not in candidates:
                    candidates.append(email)
            except:
                continue
        
        # Test candidates (limit to first 5 for performance)
        for email in candidates[:5]:
            try:
                verification = await self.verify_email_comprehensive(email)
                if verification["confidence_score"] >= 0.7:
                    suggestions.append({
                        "email": email,
                        "confidence": verification["confidence_score"],
                        "method": "pattern_generation"
                    })
            except:
                continue
        
        return suggestions
    
    def _extract_domain(self, domain_or_company: str) -> Optional[str]:
        """Extract domain from company name or URL"""
        if not domain_or_company:
            return None
        
        # If it's already a domain
        if '.' in domain_or_company and not ' ' in domain_or_company:
            # Clean up domain
            domain = domain_or_company.lower()
            domain = re.sub(r'^https?://', '', domain)
            domain = re.sub(r'^www\.', '', domain)
            domain = domain.split('/')[0]
            return domain
        
        # Try to guess domain from company name
        company_clean = re.sub(r'[^a-zA-Z0-9\s]', '', domain_or_company.lower())
        company_clean = re.sub(r'\b(inc|llc|corp|company|ltd|limited)\b', '', company_clean)
        company_clean = company_clean.strip().replace(' ', '')
        
        if company_clean:
            return f"{company_clean}.com"
        
        return None
    
    async def batch_verify_emails(self, emails: List[str], 
                                contact_data: List[Dict] = None) -> Dict[str, Dict]:
        """Verify multiple emails in batch"""
        results = {}
        
        for i, email in enumerate(emails):
            contact_info = contact_data[i] if contact_data and i < len(contact_data) else {}
            
            result = await self.verify_email_comprehensive(
                email=email,
                first_name=contact_info.get('first_name'),
                last_name=contact_info.get('last_name'),
                company=contact_info.get('company'),
                domain=contact_info.get('domain')
            )
            
            results[email] = result
            
            # Small delay to be respectful to SMTP servers
            await asyncio.sleep(0.2)
        
        return results