#!/bin/bash
# Production Start Script for K-AI API
# ====================================
# This script starts the K-AI API in production mode

cd ~/kai-api

echo "🚀 Starting K-AI API in production mode..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
playwright install chromium

# Create necessary directories
mkdir -p static
mkdir -p /tmp/opencode_sessions

# Set environment variables for production
export PYTHONUNBUFFERED=1
export ENVIRONMENT=production
export PORT=8000
export HOST=0.0.0.0

# Check if .env file exists and source it
if [ -f ".env" ]; then
    echo "🔑 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

echo ""
echo "========================================"
echo "🌐 K-AI API is starting!"
echo "========================================"
echo ""
echo "The API will be available at:"
echo "  • Local: http://localhost:8000"
echo "  • Admin: http://localhost:8000/qazmlp"
echo ""
echo "To run in background with auto-restart, use:"
echo "  ./run-daemon.sh"
echo ""
echo "Starting server..."
echo ""

# Start the server
exec uvicorn main:app --host $HOST --port $PORT --workers 1
