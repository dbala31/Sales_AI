import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
import re


class EnhancedPhoneService:
    """Enhanced phone validation using libphonenumber (free)"""
    
    def __init__(self):
        # Common country codes for business numbers
        self.business_regions = ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'JP', 'IN']
        
        # Known mobile carriers that might indicate personal vs business
        self.mobile_indicators = [
            'mobile', 'cellular', 'cell', 'wireless', 'sprint', 'verizon',
            'att', 't-mobile', 'tmobile', 'virgin', 'boost'
        ]
        
        # Business line indicators
        self.business_indicators = [
            'business', 'corporate', 'office', 'main', 'headquarters', 'hq'
        ]
    
    def validate_phone_comprehensive(self, phone: str, 
                                   country_hint: str = "US",
                                   company: str = None) -> Dict[str, Any]:
        """Comprehensive phone validation and analysis"""
        
        result = {
            "phone": phone,
            "is_valid": False,
            "confidence_score": 0.0,
            "formatted": {
                "e164": None,
                "international": None,
                "national": None,
                "rfc3966": None
            },
            "analysis": {
                "country": None,
                "region": None,
                "carrier": None,
                "line_type": None,
                "timezone": None,
                "is_mobile": False,
                "is_business_likely": False
            },
            "validation_details": {
                "length_valid": False,
                "format_valid": False,
                "region_valid": False,
                "possible": False
            },
            "issues": []
        }
        
        if not phone:
            result["issues"].append("Phone number is empty")
            return result
        
        try:
            # Clean and normalize input
            cleaned_phone = self._clean_phone_input(phone)
            
            # Parse phone number
            try:
                parsed_number = phonenumbers.parse(cleaned_phone, country_hint)
                result["analysis"]["country"] = parsed_number.country_code
            except phonenumbers.NumberParseException as e:
                result["issues"].append(f"Parse error: {e}")
                return result
            
            # Basic validation checks
            result["validation_details"]["possible"] = phonenumbers.is_possible_number(parsed_number)
            result["validation_details"]["format_valid"] = phonenumbers.is_valid_number(parsed_number)
            
            if not result["validation_details"]["possible"]:
                result["issues"].append("Phone number is not possible")
                return result
            
            if not result["validation_details"]["format_valid"]:
                result["issues"].append("Phone number format is invalid")
                return result
            
            # Format phone number in various formats
            result["formatted"]["e164"] = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.E164
            )
            result["formatted"]["international"] = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            result["formatted"]["national"] = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL
            )
            result["formatted"]["rfc3966"] = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.RFC3966
            )
            
            # Get geographic and carrier information
            try:
                result["analysis"]["region"] = geocoder.description_for_number(parsed_number, "en")
                result["analysis"]["carrier"] = carrier.name_for_number(parsed_number, "en")
                
                # Get timezone
                timezones = timezone.time_zones_for_number(parsed_number)
                if timezones:
                    result["analysis"]["timezone"] = list(timezones)[0]
                
            except Exception as e:
                logger.warning(f"Error getting phone metadata: {str(e)}")
            
            # Determine line type
            number_type = phonenumbers.number_type(parsed_number)
            result["analysis"]["line_type"] = self._get_line_type_description(number_type)
            result["analysis"]["is_mobile"] = number_type in [
                phonenumbers.PhoneNumberType.MOBILE,
                phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE
            ]
            
            # Business likelihood analysis
            result["analysis"]["is_business_likely"] = self._analyze_business_likelihood(
                parsed_number, result["analysis"], company
            )
            
            # Length validation
            result["validation_details"]["length_valid"] = self._validate_length(parsed_number)
            result["validation_details"]["region_valid"] = self._validate_region(parsed_number)
            
            # Calculate overall confidence score
            result["confidence_score"] = self._calculate_phone_confidence(result)
            result["is_valid"] = result["confidence_score"] >= 0.7
            
            return result
            
        except Exception as e:
            logger.error(f"Phone validation failed for {phone}: {str(e)}")
            result["issues"].append(f"Validation error: {str(e)}")
            return result
    
    def _clean_phone_input(self, phone: str) -> str:
        """Clean phone input for parsing"""
        # Remove common non-numeric characters but keep + for country code
        cleaned = re.sub(r'[^\d+\-\(\)\s]', '', phone.strip())
        
        # Handle common formats
        cleaned = re.sub(r'^\+?1?[\-\s]?', '+1', cleaned)  # Handle US numbers
        cleaned = re.sub(r'[\-\s\(\)]', '', cleaned)  # Remove separators
        
        return cleaned
    
    def _get_line_type_description(self, number_type) -> str:
        """Get human-readable line type description"""
        type_map = {
            phonenumbers.PhoneNumberType.FIXED_LINE: "landline",
            phonenumbers.PhoneNumberType.MOBILE: "mobile",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "landline_or_mobile",
            phonenumbers.PhoneNumberType.TOLL_FREE: "toll_free",
            phonenumbers.PhoneNumberType.PREMIUM_RATE: "premium_rate",
            phonenumbers.PhoneNumberType.SHARED_COST: "shared_cost",
            phonenumbers.PhoneNumberType.VOIP: "voip",
            phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "personal",
            phonenumbers.PhoneNumberType.PAGER: "pager",
            phonenumbers.PhoneNumberType.UAN: "universal_access",
            phonenumbers.PhoneNumberType.VOICEMAIL: "voicemail",
            phonenumbers.PhoneNumberType.UNKNOWN: "unknown"
        }
        return type_map.get(number_type, "unknown")
    
    def _analyze_business_likelihood(self, parsed_number, analysis: Dict, 
                                   company: str = None) -> bool:
        """Analyze if phone number is likely a business line"""
        business_score = 0
        
        # Line type indicators
        line_type = analysis.get("line_type", "")
        if line_type == "landline":
            business_score += 3
        elif line_type == "toll_free":
            business_score += 5
        elif line_type == "voip":
            business_score += 2
        elif line_type == "mobile":
            business_score -= 2
        
        # Carrier analysis
        carrier_name = analysis.get("carrier", "").lower()
        if carrier_name:
            if any(indicator in carrier_name for indicator in self.business_indicators):
                business_score += 2
            elif any(indicator in carrier_name for indicator in self.mobile_indicators):
                business_score -= 1
        
        # Geographic correlation with company
        if company and analysis.get("region"):
            # Simple heuristic: if company is mentioned with region keywords
            region = analysis["region"].lower()
            company_lower = company.lower()
            
            # Check for geographic correlation
            common_regions = ['new york', 'california', 'texas', 'florida', 'london', 'toronto']
            if any(reg in region for reg in common_regions):
                if any(reg in company_lower for reg in common_regions):
                    business_score += 1
        
        # Country code analysis
        country_code = parsed_number.country_code
        if country_code in [1, 44, 61, 49, 33]:  # US, UK, AU, DE, FR - common business regions
            business_score += 1
        
        return business_score >= 3
    
    def _validate_length(self, parsed_number) -> bool:
        """Validate phone number length"""
        # Get national number without country code
        national_number = str(parsed_number.national_number)
        
        # Most valid phone numbers are between 7-15 digits
        return 7 <= len(national_number) <= 15
    
    def _validate_region(self, parsed_number) -> bool:
        """Validate phone number region"""
        try:
            # Check if the number is valid for its region
            region_code = phonenumbers.region_code_for_number(parsed_number)
            if not region_code:
                return False
            
            # Re-parse with detected region and check validity
            reparsed = phonenumbers.parse(str(parsed_number.national_number), region_code)
            return phonenumbers.is_valid_number(reparsed)
            
        except:
            return False
    
    def _calculate_phone_confidence(self, result: Dict) -> float:
        """Calculate overall confidence score for phone number"""
        score = 0.0
        
        # Basic validation (40%)
        if result["validation_details"]["format_valid"]:
            score += 0.25
        if result["validation_details"]["possible"]:
            score += 0.1
        if result["validation_details"]["length_valid"]:
            score += 0.05
        
        # Line type analysis (20%)
        line_type = result["analysis"]["line_type"]
        if line_type in ["landline", "toll_free"]:
            score += 0.2
        elif line_type in ["mobile", "voip"]:
            score += 0.15
        elif line_type != "unknown":
            score += 0.1
        
        # Geographic data availability (15%)
        if result["analysis"]["region"]:
            score += 0.1
        if result["analysis"]["carrier"]:
            score += 0.05
        
        # Business likelihood (15%)
        if result["analysis"]["is_business_likely"]:
            score += 0.15
        elif not result["analysis"]["is_mobile"]:
            score += 0.1
        
        # Formatting success (10%)
        if result["formatted"]["e164"]:
            score += 0.1
        
        return min(score, 1.0)
    
    def normalize_phone_number(self, phone: str, country_hint: str = "US") -> Optional[str]:
        """Normalize phone number to E164 format"""
        try:
            cleaned = self._clean_phone_input(phone)
            parsed = phonenumbers.parse(cleaned, country_hint)
            
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            
        except:
            pass
        
        return None
    
    def deduplicate_phone_numbers(self, phone_list: List[str]) -> List[Dict[str, Any]]:
        """Deduplicate phone numbers and return normalized versions"""
        seen_numbers = set()
        deduplicated = []
        
        for phone in phone_list:
            normalized = self.normalize_phone_number(phone)
            
            if normalized and normalized not in seen_numbers:
                seen_numbers.add(normalized)
                validation = self.validate_phone_comprehensive(phone)
                
                deduplicated.append({
                    "original": phone,
                    "normalized": normalized,
                    "is_valid": validation["is_valid"],
                    "confidence": validation["confidence_score"],
                    "line_type": validation["analysis"]["line_type"]
                })
        
        return deduplicated
    
    def batch_validate_phones(self, phones: List[str], 
                            country_hints: List[str] = None,
                            companies: List[str] = None) -> Dict[str, Dict]:
        """Validate multiple phone numbers"""
        results = {}
        
        for i, phone in enumerate(phones):
            country_hint = country_hints[i] if country_hints and i < len(country_hints) else "US"
            company = companies[i] if companies and i < len(companies) else None
            
            result = self.validate_phone_comprehensive(phone, country_hint, company)
            results[phone] = result
        
        return results
    
    def suggest_phone_corrections(self, phone: str, country_hint: str = "US") -> List[str]:
        """Suggest corrections for invalid phone numbers"""
        suggestions = []
        
        if not phone:
            return suggestions
        
        # Try different formatting approaches
        cleaned = re.sub(r'[^\d]', '', phone)
        
        # Common correction patterns
        patterns = [
            f"+1{cleaned}",  # Add US country code
            f"+1{cleaned[-10:]}",  # Take last 10 digits with US code
            f"{cleaned}",  # Just digits
            f"{cleaned[1:]}" if cleaned.startswith('1') and len(cleaned) == 11 else None,  # Remove leading 1
        ]
        
        for pattern in patterns:
            if pattern:
                try:
                    parsed = phonenumbers.parse(pattern, country_hint)
                    if phonenumbers.is_valid_number(parsed):
                        formatted = phonenumbers.format_number(
                            parsed, phonenumbers.PhoneNumberFormat.E164
                        )
                        if formatted not in suggestions:
                            suggestions.append(formatted)
                except:
                    continue
        
        return suggestions[:3]  # Return top 3 suggestions