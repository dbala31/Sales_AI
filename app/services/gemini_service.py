import google.generativeai as genai
from typing import Dict, List, Any, Optional
from loguru import logger
from app.core.config import settings
import json


class GeminiService:
    """Google Gemini AI integration for enhanced contact analysis"""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            logger.info("Gemini service initialized successfully")
        else:
            self.model = None
            logger.warning("Gemini API key not configured")
    
    async def analyze_contact_quality(self, contact_data: Dict, verification_results: Dict = None) -> Dict[str, Any]:
        """Use Gemini to analyze contact quality and provide insights"""
        if not self.model:
            return {"error": "Gemini not configured", "score": 0}
        
        try:
            prompt = self._build_contact_analysis_prompt(contact_data, verification_results)
            response = self.model.generate_content(prompt)
            
            # Parse Gemini response
            analysis = self._parse_gemini_response(response.text)
            
            logger.info(f"Gemini analysis completed for contact: {contact_data.get('email')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {str(e)}")
            return {"error": str(e), "score": 0}
    
    def _build_contact_analysis_prompt(self, contact_data: Dict, verification_results: Dict = None) -> str:
        """Build prompt for Gemini contact analysis"""
        
        prompt = f"""
Analyze the following sales contact data and provide a quality assessment:

CONTACT DATA:
- Name: {contact_data.get('first_name', 'N/A')} {contact_data.get('last_name', 'N/A')}
- Email: {contact_data.get('email', 'N/A')}
- Phone: {contact_data.get('phone', 'N/A')}
- Company: {contact_data.get('company', 'N/A')}
- Job Title: {contact_data.get('job_title', 'N/A')}
- LinkedIn: {contact_data.get('linkedin_url', 'N/A')}

VERIFICATION RESULTS:
"""
        
        if verification_results:
            if 'linkedin' in verification_results:
                linkedin = verification_results['linkedin']
                prompt += f"- LinkedIn Verified: {linkedin.get('verified', False)}\n"
                if linkedin.get('profile_data'):
                    prompt += f"- LinkedIn Profile Active: {linkedin['profile_data'].get('profile_active', 'Unknown')}\n"
            
            if 'salesforce' in verification_results:
                salesforce = verification_results['salesforce']
                prompt += f"- Salesforce Match: {salesforce.get('verified', False)}\n"
                prompt += f"- Is Duplicate: {salesforce.get('is_duplicate', False)}\n"
        
        prompt += """
Please analyze this contact and provide:

1. Overall Quality Score (0-100)
2. Key Strengths (what makes this a good lead)
3. Potential Concerns (what might be problematic)
4. Likelihood of Response (High/Medium/Low)
5. Recommended Action (Contact/Skip/Research More)
6. Insights about the contact's role and decision-making authority

Respond in the following JSON format:
{
    "quality_score": <number 0-100>,
    "response_likelihood": "<High/Medium/Low>",
    "recommended_action": "<Contact/Skip/Research More>",
    "strengths": ["<strength1>", "<strength2>"],
    "concerns": ["<concern1>", "<concern2>"],
    "authority_level": "<High/Medium/Low>",
    "insights": "<detailed analysis>",
    "contact_priority": "<High/Medium/Low>"
}
"""
        
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response into structured data"""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                analysis = json.loads(json_str)
                
                # Validate required fields
                if 'quality_score' not in analysis:
                    analysis['quality_score'] = 50  # Default score
                
                return analysis
            else:
                # Fallback parsing if JSON format is not found
                return self._fallback_parse(response_text)
                
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini JSON response, using fallback")
            return self._fallback_parse(response_text)
    
    def _fallback_parse(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing for non-JSON responses"""
        lines = response_text.lower().split('\n')
        
        # Extract quality score
        quality_score = 50  # Default
        for line in lines:
            if 'quality' in line and ('score' in line or 'rating' in line):
                numbers = [int(s) for s in line.split() if s.isdigit()]
                if numbers:
                    quality_score = min(100, max(0, numbers[0]))
                    break
        
        # Determine response likelihood
        response_likelihood = "Medium"
        if any(word in response_text.lower() for word in ['excellent', 'high quality', 'strong']):
            response_likelihood = "High"
        elif any(word in response_text.lower() for word in ['poor', 'low quality', 'weak']):
            response_likelihood = "Low"
        
        return {
            "quality_score": quality_score,
            "response_likelihood": response_likelihood,
            "recommended_action": "Contact" if quality_score > 70 else "Research More",
            "strengths": ["Professional email domain", "Complete contact information"],
            "concerns": ["Limited verification data"],
            "authority_level": "Medium",
            "insights": response_text[:500],  # First 500 chars
            "contact_priority": "Medium"
        }
    
    async def analyze_batch_insights(self, batch_results: List[Dict]) -> Dict[str, Any]:
        """Analyze batch results and provide insights"""
        if not self.model:
            return {"error": "Gemini not configured"}
        
        try:
            # Summarize batch statistics
            total_contacts = len(batch_results)
            verified_contacts = sum(1 for r in batch_results if r.get('is_verified'))
            avg_quality = sum(r.get('quality_score', 0) for r in batch_results) / total_contacts if total_contacts > 0 else 0
            
            # Sample contacts for analysis
            sample_contacts = batch_results[:5]  # Analyze first 5 contacts
            
            prompt = f"""
Analyze the following batch processing results for a sales contact verification system:

BATCH SUMMARY:
- Total Contacts: {total_contacts}
- Verified Contacts: {verified_contacts}
- Success Rate: {(verified_contacts/total_contacts)*100:.1f}%
- Average Quality Score: {avg_quality:.1f}

SAMPLE CONTACTS:
"""
            
            for i, contact in enumerate(sample_contacts, 1):
                prompt += f"""
Contact {i}:
- Email: {contact.get('email', 'N/A')}
- Company: {contact.get('company', 'N/A')}
- Verified: {contact.get('is_verified', False)}
- Quality Score: {contact.get('quality_score', 0)}
"""
            
            prompt += """
Please provide:
1. Overall assessment of the batch quality
2. Common patterns in successful verifications
3. Recommendations for improving verification rates
4. Industry insights based on the companies/domains
5. Suggested next steps for sales outreach

Respond in JSON format:
{
    "batch_assessment": "<High/Medium/Low quality>",
    "success_patterns": ["<pattern1>", "<pattern2>"],
    "improvement_recommendations": ["<rec1>", "<rec2>"],
    "industry_insights": "<insights>",
    "outreach_recommendations": ["<rec1>", "<rec2>"],
    "overall_score": <0-100>
}
"""
            
            response = self.model.generate_content(prompt)
            insights = self._parse_gemini_response(response.text)
            
            logger.info(f"Gemini batch analysis completed for {total_contacts} contacts")
            return insights
            
        except Exception as e:
            logger.error(f"Gemini batch analysis failed: {str(e)}")
            return {"error": str(e)}
    
    async def suggest_email_improvements(self, email: str, company: str = None) -> Dict[str, Any]:
        """Suggest alternative email formats if current email seems invalid"""
        if not self.model:
            return {"error": "Gemini not configured"}
        
        try:
            prompt = f"""
Analyze this email address and suggest improvements or alternatives if needed:

Email: {email}
Company: {company or 'Unknown'}

Please assess:
1. Is this email format valid and professional?
2. If the email seems suspicious or incorrect, suggest 2-3 alternative formats
3. Provide confidence level for the original email

Respond in JSON format:
{{
    "is_valid": <true/false>,
    "confidence": <0-100>,
    "suggested_alternatives": ["<alt1>", "<alt2>"],
    "issues": ["<issue1>", "<issue2>"],
    "recommendations": "<text>"
}}
"""
            
            response = self.model.generate_content(prompt)
            suggestions = self._parse_gemini_response(response.text)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Gemini email analysis failed: {str(e)}")
            return {"error": str(e)}