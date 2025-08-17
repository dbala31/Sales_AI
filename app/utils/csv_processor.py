import pandas as pd
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import chardet
from loguru import logger


class CSVProcessor:
    """Handles CSV file processing and data standardization"""
    
    FIELD_MAPPINGS = {
        'first_name': ['first_name', 'firstname', 'first', 'fname', 'given_name'],
        'last_name': ['last_name', 'lastname', 'last', 'lname', 'surname', 'family_name'],
        'email': ['email', 'email_address', 'e_mail', 'mail', 'email_addr'],
        'phone': ['phone', 'phone_number', 'telephone', 'tel', 'mobile', 'cell'],
        'company': ['company', 'company_name', 'organization', 'org', 'employer'],
        'job_title': ['job_title', 'title', 'position', 'role', 'job', 'designation'],
        'linkedin_url': ['linkedin_url', 'linkedin', 'li_url', 'linkedin_profile']
    }
    
    def __init__(self):
        self.required_fields = ['email', 'phone']
    
    def detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except Exception:
            return 'utf-8'
    
    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to match our schema"""
        df_copy = df.copy()
        
        # Convert column names to lowercase and replace spaces/special chars
        df_copy.columns = [
            re.sub(r'[^\w]', '_', col.lower().strip()) 
            for col in df_copy.columns
        ]
        
        # Map columns to standard field names
        column_mapping = {}
        for standard_field, variations in self.FIELD_MAPPINGS.items():
            for col in df_copy.columns:
                if col in variations or any(var in col for var in variations):
                    column_mapping[col] = standard_field
                    break
        
        df_copy = df_copy.rename(columns=column_mapping)
        return df_copy
    
    def validate_and_clean_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Validate and clean contact data"""
        stats = {
            'total_rows': int(len(df)),
            'valid_rows': 0,
            'missing_email': 0,
            'missing_phone': 0,
            'invalid_email': 0,
            'invalid_phone': 0,
            'duplicates_removed': 0
        }
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Count missing required fields
        stats['missing_email'] = int(df['email'].isna().sum()) if 'email' in df.columns else int(len(df))
        stats['missing_phone'] = int(df['phone'].isna().sum()) if 'phone' in df.columns else int(len(df))
        
        # Validate email format
        if 'email' in df.columns:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            valid_emails = df['email'].str.match(email_pattern, na=False)
            stats['invalid_email'] = int((~valid_emails & df['email'].notna()).sum())
            df.loc[~valid_emails, 'email'] = None
        
        # Validate phone format
        if 'phone' in df.columns:
            df['phone'] = df['phone'].astype(str).str.replace(r'[^\d+\-\(\)\s]', '', regex=True)
            # Keep only phones with at least 10 digits
            phone_digits = df['phone'].str.extract(r'(\d+)', expand=False).str.len()
            valid_phones = phone_digits >= 10
            stats['invalid_phone'] = int((~valid_phones & df['phone'].notna()).sum())
            df.loc[~valid_phones, 'phone'] = None
        
        # Remove rows missing both email and phone
        initial_count = len(df)
        df = df.dropna(subset=['email', 'phone'], how='all')
        
        # Remove duplicates based on email
        if 'email' in df.columns:
            duplicate_count = int(df.duplicated(subset=['email']).sum())
            df = df.drop_duplicates(subset=['email'])
            stats['duplicates_removed'] = duplicate_count
        
        stats['valid_rows'] = int(len(df))
        stats['rows_removed'] = int(initial_count - len(df))
        
        return df, stats
    
    def process_csv(self, file_path: str) -> Tuple[pd.DataFrame, Dict]:
        """Process CSV file and return cleaned data with statistics"""
        try:
            # Detect encoding
            encoding = self.detect_encoding(file_path)
            logger.info(f"Detected encoding: {encoding}")
            
            # Read CSV
            df = pd.read_csv(file_path, encoding=encoding)
            logger.info(f"Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
            
            # Normalize column names
            df = self.normalize_column_names(df)
            logger.info(f"Normalized columns: {list(df.columns)}")
            
            # Validate and clean data
            df_clean, stats = self.validate_and_clean_data(df)
            logger.info(f"Cleaning stats: {stats}")
            
            # Add any missing columns with default values
            for field in self.FIELD_MAPPINGS.keys():
                if field not in df_clean.columns:
                    df_clean[field] = None
            
            return df_clean, stats
            
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            raise Exception(f"Failed to process CSV file: {str(e)}")
    
    def convert_to_contact_records(self, df: pd.DataFrame) -> List[Dict]:
        """Convert DataFrame to list of contact dictionaries"""
        contacts = []
        
        for _, row in df.iterrows():
            contact = {
                'first_name': self._clean_string(row.get('first_name')),
                'last_name': self._clean_string(row.get('last_name')),
                'email': self._clean_string(row.get('email')),
                'phone': self._clean_string(row.get('phone')),
                'company': self._clean_string(row.get('company')),
                'job_title': self._clean_string(row.get('job_title')),
                'linkedin_url': self._clean_string(row.get('linkedin_url'))
            }
            
            # Only add contacts that have at least email or phone
            if contact['email'] or contact['phone']:
                contacts.append(contact)
        
        return contacts
    
    def _clean_string(self, value) -> Optional[str]:
        """Clean string value"""
        if pd.isna(value) or value is None:
            return None
        
        cleaned = str(value).strip()
        return cleaned if cleaned else None
    
    def export_to_csv(self, contacts: List[Dict], file_path: str) -> None:
        """Export cleaned contacts to CSV"""
        df = pd.DataFrame(contacts)
        df.to_csv(file_path, index=False)
        logger.info(f"Exported {len(contacts)} contacts to {file_path}")