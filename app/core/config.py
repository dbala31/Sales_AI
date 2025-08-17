from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://username:password@localhost:5432/sales_ai"
    redis_url: str = "redis://localhost:6379/0"
    
    # Email Verification Settings
    email_verification_timeout: int = 10
    smtp_connection_timeout: int = 5
    max_email_suggestions: int = 5
    
    # Salesforce API
    salesforce_username: Optional[str] = None
    salesforce_password: Optional[str] = None
    salesforce_security_token: Optional[str] = None
    salesforce_domain: Optional[str] = None
    
    # Gemini API
    gemini_api_key: Optional[str] = None
    
    # Application
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File handling
    upload_directory: str = "./uploads"
    max_file_size: int = 50000000  # 50MB
    
    # Verification settings
    default_quality_threshold: int = 30
    max_batch_size: int = 10000
    verification_rate_limit: int = 30  # requests per minute for external services
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    class Config:
        env_file = ".env"


settings = Settings()