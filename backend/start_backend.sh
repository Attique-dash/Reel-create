#!/bin/bash

# Start Backend Server with Proper Configuration
# This script ensures the environment is properly set up before starting the API

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          Starting Video Processor Backend API                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

echo "✅ Virtual environment is active"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env with MongoDB and API configuration."
    exit 1
fi

echo "✅ Configuration file found (.env)"
echo ""

# Show configuration status
echo "📋 Configuration Summary:"
echo "─────────────────────────────────────────────────────────"

if grep -q "mongodb+srv" .env; then
    echo "✅ Using MongoDB Atlas (Cloud)"
elif grep -q "localhost:27017" .env; then
    echo "⚠️  Using Local MongoDB (must be running on localhost:27017)"
else
    echo "❓ MongoDB configuration unclear"
fi

if grep -q "GEMINI_API_KEY=your-gemini-api-key" .env; then
    echo "⚠️  GEMINI_API_KEY not configured (get from https://aistudio.google.com/app/apikey)"
else
    echo "✅ GEMINI_API_KEY configured"
fi

echo ""
echo "🚀 Starting backend server..."
echo "   API running on: http://localhost:8000"
echo "   Docs running on: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "═════════════════════════════════════════════════════════"
echo ""

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
