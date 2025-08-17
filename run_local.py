#!/usr/bin/env python3
"""
Quick local setup script for Sales AI platform
Run this instead of Docker for faster testing
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path

def setup_environment():
    """Setup local environment"""
    print("🚀 Setting up Sales AI Contact Verification Platform locally...")
    
    # Create .env file if it doesn't exist
    env_file = Path('.env')
    if not env_file.exists():
        print("📝 Creating .env file...")
        with open('.env', 'w') as f:
            f.write("""# Local Development Configuration
DATABASE_URL=sqlite:///./sales_ai.db
REDIS_URL=redis://localhost:6379/0

# Add your Gemini API key here
GEMINI_API_KEY=your_gemini_api_key_here

# Email Verification Settings
EMAIL_VERIFICATION_TIMEOUT=10
SMTP_CONNECTION_TIMEOUT=5
MAX_EMAIL_SUGGESTIONS=5

# Application Settings
SECRET_KEY=local-development-key-change-in-production
DEFAULT_QUALITY_THRESHOLD=80
MAX_BATCH_SIZE=10000
VERIFICATION_RATE_LIMIT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Leave Salesforce empty to use mock data (no API needed)
# SALESFORCE_USERNAME=
# SALESFORCE_PASSWORD=
# SALESFORCE_SECURITY_TOKEN=
""")
        print("✅ Created .env file")
    
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    print("✅ Created directories")
    
    # Create SQLite database
    if not os.path.exists('sales_ai.db'):
        print("🗄️ Creating SQLite database...")
        conn = sqlite3.connect('sales_ai.db')
        conn.close()
        print("✅ Database created")
    
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        import pandas
        import sqlalchemy
        print("✅ Core dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception:
        print("⚠️ Redis not running. Celery tasks will be disabled.")
        print("💡 To start Redis:")
        print("   Mac: brew install redis && brew services start redis")
        print("   Ubuntu: sudo apt install redis-server && sudo systemctl start redis")
        print("   Windows: Download from https://redis.io/download")
        return False

def start_application():
    """Start the FastAPI application"""
    print("\n🚀 Starting Sales AI platform...")
    print("📍 URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("\n⏹️ Press Ctrl+C to stop\n")
    
    try:
        # Run uvicorn
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'app.main:app', 
            '--reload', 
            '--host', '0.0.0.0', 
            '--port', '8000'
        ])
    except KeyboardInterrupt:
        print("\n👋 Stopped Sales AI platform")

if __name__ == "__main__":
    if setup_environment():
        if check_dependencies():
            redis_available = check_redis()
            if not redis_available:
                print("⚠️ Continuing without Redis (background tasks disabled)")
            
            print("\n" + "="*50)
            print("🎯 QUICK TEST INSTRUCTIONS:")
            print("1. Open http://localhost:8000 in your browser")
            print("2. Click 'Download Sample CSV' to get test data")
            print("3. Upload the CSV to test verification")
            print("4. Check results and download verified contacts")
            print("="*50 + "\n")
            
            start_application()
        else:
            print("\n💡 Install dependencies first:")
            print("pip install -r requirements.txt")
    else:
        print("❌ Setup failed")