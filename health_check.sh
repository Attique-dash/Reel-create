#!/bin/bash

# Video Processor - System Health Check
# Run this to verify all services are properly configured

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     VIDEO PROCESSOR - SYSTEM HEALTH CHECK                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_count=0
success_count=0

# Function to check status
check_status() {
    local name=$1
    local command=$2
    
    check_count=$((check_count + 1))
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $name"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}❌${NC} $name"
    fi
}

# Function to check service running
check_service() {
    local name=$1
    local host=$2
    local port=$3
    
    check_count=$((check_count + 1))
    
    if timeout 2 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $name (running on $host:$port)"
        success_count=$((success_count + 1))
    else
        echo -e "${RED}❌${NC} $name (not accessible on $host:$port)"
    fi
}

echo "🔍 Checking System Requirements..."
echo "─────────────────────────────────────────────────────────────"

# Check system commands
check_status "Python installed" "command -v python3"
check_status "Node.js installed" "command -v node"
check_status "Docker installed" "command -v docker"
check_status "FFmpeg installed" "command -v ffmpeg"

echo ""
echo "🔍 Checking Python Dependencies..."
echo "─────────────────────────────────────────────────────────────"

if [ -d "backend/venv" ]; then
    echo -e "${GREEN}✅${NC} Python virtual environment exists (backend/venv)"
    success_count=$((success_count + 1))
    
    # Check if venv is activated or can be used
    source backend/venv/bin/activate 2>/dev/null || true
else
    echo -e "${YELLOW}⚠️ ${NC} Virtual environment not found at backend/venv"
    echo "   Create it with: python3 -m venv backend/venv"
fi
check_count=$((check_count + 1))

echo ""
echo "🔍 Checking Frontend Setup..."
echo "─────────────────────────────────────────────────────────────"

if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✅${NC} Frontend dependencies installed (frontend/node_modules)"
    success_count=$((success_count + 1))
else
    echo -e "${YELLOW}⚠️ ${NC} Frontend dependencies not installed"
    echo "   Install with: cd frontend && npm install"
fi
check_count=$((check_count + 1))

echo ""
echo "🔍 Checking Configuration Files..."
echo "─────────────────────────────────────────────────────────────"

check_status "Backend .env exists" "[ -f backend/.env ]"
check_status "Backend .env.example exists" "[ -f backend/.env.example ]"

echo ""
echo "🔍 Checking Running Services..."
echo "─────────────────────────────────────────────────────────────"

check_service "MongoDB" "localhost" "27017"
check_service "Redis" "localhost" "6379"
check_service "Backend API" "localhost" "8000"
check_service "Frontend" "localhost" "3000"

echo ""
echo "🔍 Checking Backend Files..."
echo "─────────────────────────────────────────────────────────────"

check_status "Celery worker module" "[ -f backend/app/workers/celery_worker.py ]"
check_status "Startup script exists" "[ -f backend/start_celery_worker.sh ]"
check_status "Setup guide exists" "[ -f SETUP_GUIDE.md ]"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                      HEALTH CHECK RESULTS                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

percentage=$((success_count * 100 / check_count))
echo "Status: $success_count/$check_count checks passed ($percentage%)"
echo ""

if [ $success_count -eq $check_count ]; then
    echo -e "${GREEN}🎉 All checks passed! Your system is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Make sure services are running (MongoDB, Redis)"
    echo "2. Start backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "3. Start Celery: cd backend && source venv/bin/activate && ./start_celery_worker.sh"
    echo "4. Start frontend: cd frontend && npm run dev"
    echo "5. Access at http://localhost:3000"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some checks failed. Please review above for details.${NC}"
    echo ""
    echo "Common fixes:"
    echo "• Create venv: python3 -m venv backend/venv"
    echo "• Install deps: pip install -r backend/requirements.txt"
    echo "• Install npm: cd frontend && npm install"
    echo "• Start MongoDB: mongod or docker run -d -p 27017:27017 mongo"
    echo "• Start Redis: redis-server or docker run -d -p 6379:6379 redis"
    echo ""
    echo "For more help, see: SETUP_GUIDE.md"
    exit 1
fi
