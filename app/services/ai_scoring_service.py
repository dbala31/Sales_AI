import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import joblib
from typing import Dict, List, Any, Optional
from loguru import logger
import os


class AIQualityScorer:
    """AI-powered contact quality scoring system"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'has_email', 'has_phone', 'has_linkedin', 'has_company', 'has_job_title',
            'email_domain_score', 'phone_validity_score', 'linkedin_verified',
            'salesforce_match', 'data_completeness_score'
        ]
        self.model_path = "models/quality_scorer.joblib"
        self.scaler_path = "models/scaler.joblib"
        
        # Load pre-trained model if available
        self._load_model()
    
    def _create_training_data(self) -> tuple:
        """Create synthetic training data for the quality scoring model"""
        np.random.seed(42)
        n_samples = 10000
        
        # Generate synthetic features
        data = {
            'has_email': np.random.choice([0, 1], n_samples, p=[0.1, 0.9]),
            'has_phone': np.random.choice([0, 1], n_samples, p=[0.2, 0.8]),
            'has_linkedin': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
            'has_company': np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
            'has_job_title': np.random.choice([0, 1], n_samples, p=[0.4, 0.6]),
            'email_domain_score': np.random.uniform(0, 1, n_samples),
            'phone_validity_score': np.random.uniform(0, 1, n_samples),
            'linkedin_verified': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
            'salesforce_match': np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
            'data_completeness_score': np.random.uniform(0, 1, n_samples)
        }
        
        df = pd.DataFrame(data)
        
        # Create target variable based on feature importance
        quality_score = (
            df['has_email'] * 0.25 +
            df['has_phone'] * 0.20 +
            df['email_domain_score'] * 0.15 +
            df['linkedin_verified'] * 0.15 +
            df['phone_validity_score'] * 0.10 +
            df['data_completeness_score'] * 0.10 +
            df['has_company'] * 0.05
        )
        
        # Add some noise
        quality_score += np.random.normal(0, 0.1, n_samples)
        quality_score = np.clip(quality_score, 0, 1)
        
        # Convert to binary classification (high quality vs low quality)
        y = (quality_score > 0.7).astype(int)
        
        return df[self.feature_columns], y, quality_score
    
    def train_model(self) -> Dict[str, float]:
        """Train the quality scoring model"""
        try:
            logger.info("Training AI quality scoring model...")
            
            # Create training data
            X, y, quality_scores = self._create_training_data()
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Save model and scaler
            self._save_model()
            
            logger.info(f"Model trained successfully with accuracy: {accuracy:.3f}")
            
            return {
                "accuracy": accuracy,
                "feature_importance": dict(zip(
                    self.feature_columns,
                    self.model.feature_importances_
                ))
            }
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise
    
    def _load_model(self) -> bool:
        """Load pre-trained model and scaler"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("Loaded pre-trained quality scoring model")
                return True
        except Exception as e:
            logger.warning(f"Could not load pre-trained model: {str(e)}")
        
        return False
    
    def _save_model(self):
        """Save trained model and scaler"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Model and scaler saved successfully")
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
    
    def extract_features(self, contact_data: Dict, linkedin_result: Dict = None, 
                        salesforce_result: Dict = None) -> Dict[str, float]:
        """Extract features from contact data for scoring"""
        features = {}
        
        # Basic data completeness
        features['has_email'] = 1.0 if contact_data.get('email') else 0.0
        features['has_phone'] = 1.0 if contact_data.get('phone') else 0.0
        features['has_linkedin'] = 1.0 if contact_data.get('linkedin_url') else 0.0
        features['has_company'] = 1.0 if contact_data.get('company') else 0.0
        features['has_job_title'] = 1.0 if contact_data.get('job_title') else 0.0
        
        # Email domain scoring
        features['email_domain_score'] = self._score_email_domain(contact_data.get('email'))
        
        # Phone validity scoring
        features['phone_validity_score'] = self._score_phone_validity(contact_data.get('phone'))
        
        # LinkedIn verification results
        if linkedin_result:
            features['linkedin_verified'] = 1.0 if linkedin_result.get('verified') else 0.0
        else:
            features['linkedin_verified'] = 0.0
        
        # Salesforce verification results
        if salesforce_result:
            features['salesforce_match'] = 1.0 if salesforce_result.get('verified') else 0.0
        else:
            features['salesforce_match'] = 0.0
        
        # Overall data completeness score
        features['data_completeness_score'] = self._calculate_completeness_score(contact_data)
        
        return features
    
    def _score_email_domain(self, email: str) -> float:
        """Score email domain quality"""
        if not email or '@' not in email:
            return 0.0
        
        domain = email.split('@')[1].lower()
        
        # Business domains score higher
        business_indicators = [
            'corp.com', 'inc.com', 'llc.com', 'company.com',
            'group.com', 'enterprises.com', 'solutions.com'
        ]
        
        # Free email providers score lower
        free_providers = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'live.com'
        ]
        
        if any(bi in domain for bi in business_indicators):
            return 0.9
        elif domain in free_providers:
            return 0.3
        elif '.' in domain and len(domain.split('.')) >= 2:
            # Custom business domain
            return 0.7
        else:
            return 0.2
    
    def _score_phone_validity(self, phone: str) -> float:
        """Score phone number validity"""
        if not phone:
            return 0.0
        
        # Remove non-digits
        digits = ''.join(filter(str.isdigit, phone))
        
        if len(digits) == 10:
            return 0.9  # US phone number
        elif len(digits) == 11 and digits.startswith('1'):
            return 0.9  # US phone number with country code
        elif len(digits) >= 10:
            return 0.7  # International number
        else:
            return 0.2  # Too short
    
    def _calculate_completeness_score(self, contact_data: Dict) -> float:
        """Calculate overall data completeness score"""
        fields = ['first_name', 'last_name', 'email', 'phone', 'company', 'job_title']
        complete_fields = sum(1 for field in fields if contact_data.get(field))
        return complete_fields / len(fields)
    
    def score_contact(self, contact_data: Dict, linkedin_result: Dict = None,
                     salesforce_result: Dict = None) -> Dict[str, Any]:
        """Score a single contact's quality"""
        try:
            # Ensure model is available
            if self.model is None:
                logger.warning("No trained model available, training new model...")
                self.train_model()
            
            # Extract features
            features = self.extract_features(contact_data, linkedin_result, salesforce_result)
            
            # Prepare feature vector
            feature_vector = np.array([features[col] for col in self.feature_columns]).reshape(1, -1)
            feature_vector_scaled = self.scaler.transform(feature_vector)
            
            # Get prediction probability
            quality_probability = self.model.predict_proba(feature_vector_scaled)[0][1]
            quality_score = quality_probability * 100  # Convert to 0-100 scale
            
            # Determine quality category
            if quality_score >= 90:
                quality_category = "excellent"
            elif quality_score >= 80:
                quality_category = "good"
            elif quality_score >= 60:
                quality_category = "fair"
            else:
                quality_category = "poor"
            
            return {
                "quality_score": round(quality_score, 2),
                "quality_category": quality_category,
                "features": features,
                "model_confidence": round(max(quality_probability, 1 - quality_probability), 3)
            }
            
        except Exception as e:
            logger.error(f"Error scoring contact: {str(e)}")
            return {
                "quality_score": 0.0,
                "quality_category": "error",
                "error": str(e)
            }
    
    def batch_score(self, contacts_data: List[Dict], verification_results: Dict = None) -> List[Dict]:
        """Score multiple contacts"""
        results = []
        
        for i, contact in enumerate(contacts_data):
            contact_id = contact.get('email', str(i))
            
            linkedin_result = None
            salesforce_result = None
            
            if verification_results:
                linkedin_result = verification_results.get(f"{contact_id}_linkedin")
                salesforce_result = verification_results.get(f"{contact_id}_salesforce")
            
            score_result = self.score_contact(contact, linkedin_result, salesforce_result)
            score_result['contact_id'] = contact_id
            results.append(score_result)
        
        return results