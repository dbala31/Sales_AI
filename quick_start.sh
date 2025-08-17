#!/bin/bash

echo "🚀 Sales AI Contact Verification Platform - Quick Start"
echo "======================================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️ Redis is not running. Starting Redis..."
    if command -v brew &> /dev/null; then
        brew services start redis
    elif command -v systemctl &> /dev/null; then
        sudo systemctl start redis
    else
        echo "💡 Please start Redis manually:"
        echo "   Mac: brew install redis && brew services start redis"
        echo "   Ubuntu: sudo apt install redis-server && sudo systemctl start redis"
    fi
fi

# Run the local setup
echo "🏗️ Setting up application..."
python3 run_local.py