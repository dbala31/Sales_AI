import re
import phonenumbers
from email_validator import validate_email, EmailNotValidError
from typing import Optional, Tuple


class EmailValidator:
    """Email validation utility"""
    
    @staticmethod
    def is_valid(email: str) -> bool:
        """Check if email is valid"""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False
    
    @staticmethod
    def normalize(email: str) -> Optional[str]:
        """Normalize email address"""
        try:
            validated_email = validate_email(email)
            return validated_email.email.lower()
        except EmailNotValidError:
            return None


class PhoneValidator:
    """Phone number validation utility"""
    
    @staticmethod
    def is_valid(phone: str, country_code: str = "US") -> bool:
        """Check if phone number is valid"""
        try:
            parsed_number = phonenumbers.parse(phone, country_code)
            return phonenumbers.is_valid_number(parsed_number)
        except phonenumbers.NumberParseException:
            return False
    
    @staticmethod
    def normalize(phone: str, country_code: str = "US") -> Optional[str]:
        """Normalize phone number"""
        try:
            parsed_number = phonenumbers.parse(phone, country_code)
            if phonenumbers.is_valid_number(parsed_number):
                return phonenumbers.format_number(
                    parsed_number, 
                    phonenumbers.PhoneNumberFormat.E164
                )
        except phonenumbers.NumberParseException:
            pass
        
        return None
    
    @staticmethod
    def extract_digits(phone: str) -> str:
        """Extract only digits from phone number"""
        return re.sub(r'[^\d]', '', phone)


class LinkedInValidator:
    """LinkedIn URL validation utility"""
    
    LINKEDIN_PATTERN = re.compile(
        r'https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9\-]+/?$',
        re.IGNORECASE
    )
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if LinkedIn URL is valid"""
        if not url:
            return False
        return bool(LinkedInValidator.LINKEDIN_PATTERN.match(url.strip()))
    
    @staticmethod
    def normalize_url(url: str) -> Optional[str]:
        """Normalize LinkedIn URL"""
        if not url:
            return None
        
        url = url.strip()
        
        # Add https if missing
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Ensure it's a valid LinkedIn URL
        if LinkedInValidator.is_valid_url(url):
            return url
        
        return None