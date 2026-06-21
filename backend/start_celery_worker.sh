#!/bin/bash

# Start Celery Worker for Video Processing
# This script starts the Celery worker that processes video jobs in the background

set -e

echo "🚀 Starting Celery Worker for Video Processing..."
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated. Please activate it first:"
    echo "   source venv/bin/activate"
    exit 1
fi

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  redis-cli not found. Make sure Redis is installed and running on localhost:6379"
    echo ""
    echo "   To install Redis on macOS: brew install redis"
    echo "   To start Redis: redis-server"
    exit 1
fi

if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running! Please start Redis first:"
    echo "   redis-server"
    exit 1
fi

echo "✅ Redis is running"
echo ""

# Start Celery worker
echo "🚀 Starting Celery worker..."
echo "   Command: celery -A app.workers.celery_worker worker --loglevel=info --concurrency=2"
echo ""
echo "Press Ctrl+C to stop the worker"
echo "="*60

celery -A app.workers.celery_worker worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=100 \
    --task-events \
    --pool=solo
