# Video Processing Setup & Troubleshooting Guide

## Issue: Loading Screen Continues Indefinitely

**Problem**: When uploading a video or pasting a URL, the loading screen shows "Processing Video" but continues forever with 0% progress.

**Root Cause**: The Celery worker process is not running. Video processing tasks are queued in Redis but no worker is available to execute them, so the job status remains "pending".

---

## Solution: How to Properly Run the System

### Required Services

You need THREE services running simultaneously:

1. **MongoDB** - Database (stores job metadata)
2. **Redis** - Message broker (queues Celery tasks)
3. **FastAPI Backend** - Main API server
4. **Next.js Frontend** - UI
5. **Celery Worker** - Processes video jobs (this is what was missing!)

### Quick Start Guide

#### Terminal 1: Start MongoDB
```bash
# If using Docker (recommended):
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or if MongoDB is installed locally:
mongod
```

#### Terminal 2: Start Redis
```bash
# macOS:
redis-server

# Docker:
docker run -d -p 6379:6379 --name redis redis:latest

# Linux:
redis-server
```

#### Terminal 3: Start FastAPI Backend
```bash
cd backend
source venv/bin/activate  # or: venv\Scripts\activate on Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Terminal 4: Start Celery Worker
```bash
cd backend
source venv/bin/activate
chmod +x start_celery_worker.sh  # Make script executable
./start_celery_worker.sh

# Or run directly:
celery -A app.workers.celery_worker worker --loglevel=info --pool=solo
```

#### Terminal 5: Start Next.js Frontend
```bash
cd frontend
npm run dev
```

### Using Docker Compose (Recommended)

The easiest way is to use Docker Compose which starts everything together:

```bash
# In the project root directory:
docker-compose up

# This will start:
# - MongoDB on port 27017
# - Redis on port 6379
# - FastAPI on port 8000
# - Celery Worker (background)
# - Next.js Frontend on port 3000
```

---

## Synchronous Mode (Development Fallback)

If you don't want to set up Redis/Celery, the system has an automatic fallback:

**If Redis is NOT available**, Celery will run in **synchronous mode** (`task_always_eager=True`):
- Tasks execute immediately in the same process
- No need for a separate Celery worker
- Perfect for development
- Processing might block the API briefly

**Logs will show:**
```
⚠️  CELERY RUNNING IN SYNCHRONOUS MODE (task_always_eager=True)
   This is fine for development but means processing will block the API
```

### To Run in Synchronous Mode Only:

1. Make sure Redis is **NOT running** on localhost:6379
2. Start the FastAPI backend normally
3. Processing will happen synchronously (no separate worker needed)

---

## Backend Logs Explanation

### Normal Operation

```
INFO:     Started server process [4292]
✅ MongoDB connected successfully to video_processor
🎬 VIDEO PROCESSOR API STARTED
==============================================================
📊 Frontend: http://localhost:3000
🔌 API: http://localhost:8000
📚 Docs: http://localhost:8000/docs
==============================================================

🔵 Starting video processing task for job_id: d2c54ed9-a315-4d17-9c33-d0108d742daa
✅ Job d2c54ed9: All dependencies loaded successfully
📝 Job d2c54ed9: Updating status to 'processing'
✅ Job d2c54ed9: Status updated to processing
📥 Job d2c54ed9: Step 1/6 - Getting video source (type: file)
📂 Job d2c54ed9: Using local file: ./storage/uploads/d2c54ed9_video.mp4
✅ Job d2c54ed9: Video file ready (125.50 MB)
🎤 Job d2c54ed9: Step 2/6 - Transcribing video
✅ Job d2c54ed9: Transcription completed (duration: 600.0s, segments: 245)
🤖 Job d2c54ed9: Step 3/6 - Analyzing moments with AI
✅ Job d2c54ed9: Found 5 engaging moments for clipping
✂️ Job d2c54ed9: Step 4/6 - Creating 5 clips
✅ Job d2c54ed9: Successfully created 5 clips
📐 Job d2c54ed9: Step 5/6 - Applying smart crop to clips
✅ Job d2c54ed9: Smart crop applied to 5/5 clips
🎉 Job d2c54ed9: Processing completed successfully! Generated 5 clips
```

### Issues to Look For

#### If you see: "Redis broker not available"
```
⚠️ Redis broker not available: Connection refused
System will use synchronous processing for development.
```
**Solution**: Either start Redis, or let it run in synchronous mode

#### If you see: "Job status stuck at 'pending'"
1. Check if Celery worker is running
2. Check backend logs for processing errors
3. Check if Redis is accessible

---

## Frontend Console Network Activity

### Normal Job Status Polling

```
GET /api/process/jobs/{job_id}  →  200 OK
Response: {"status": "pending", "progress": 0, "clips": []}  ← Initially
Response: {"status": "processing", "progress": 30, "clips": []}  ← Processing
Response: {"status": "completed", "progress": 100, "clips": [...]}  ← Done!
```

### What NOT to Ignore

If the same job_id keeps returning `status: "pending"` and `progress: 0` for more than a few seconds:
- ❌ Job is NOT processing
- ❌ Celery worker is likely NOT running
- ✅ Check backend console for errors
- ✅ Make sure all services are started

---

## Common Issues & Solutions

### Issue 1: "Cannot connect to Redis"
```
Error: ConnectionError: Error 111 connecting to localhost:6379
```
**Solution**:
1. Start Redis: `redis-server`
2. Or let Celery run in synchronous mode (automatic fallback)

### Issue 2: "Job stays pending forever"
**Solution**:
1. Check if Celery worker is running
2. Look at backend logs for errors
3. Verify Redis is accessible
4. Try restarting the Celery worker

### Issue 3: "Processing takes too long"
**Solutions**:
- First run is slower (model loading)
- Check backend logs for specific step taking time
- Transcription is usually the longest step
- Make sure no other heavy processes are running

### Issue 4: "MongoDB connection failed"
```
❌ MongoDB connection failed: Connection refused
```
**Solution**:
1. Start MongoDB: `mongod` or `docker run -d -p 27017:27017 mongo`
2. Check connection string in `.env` file

---

## Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
MONGODB_URI=mongodb://localhost:27017/video_processor

# Celery (optional, defaults to local)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage
UPLOAD_DIR=./storage/uploads
PROCESSED_DIR=./storage/processed
SUBTITLES_DIR=./storage/subtitles

# Video Settings
DEFAULT_CLIP_DURATION=60
DEFAULT_NUM_CLIPS=5
DEFAULT_ASPECT_RATIO=9:16

# APIs
GEMINI_API_KEY=your-key-here
```

---

## Monitoring & Debugging

### View Celery Logs
```bash
# Backend logs show job progress
tail -f backend.log

# Or from the terminal where you started the worker
celery -A app.workers.celery_worker worker --loglevel=debug
```

### Check Job Status Directly
```bash
# In backend directory with venv activated
python
>>> from app.database.mongodb import init_db, JobRepository
>>> import asyncio
>>> 
>>> async def check():
...     await init_db()
...     job = await JobRepository.get_job("d2c54ed9-a315-4d17-9c33-d0108d742daa")
...     print(job)
>>> 
>>> asyncio.run(check())
```

### Check Redis Queue
```bash
# If Redis is running:
redis-cli
> KEYS *
> GET <key-name>
```

---

## Summary Checklist

Before processing a video, ensure:

- [ ] MongoDB is running (check logs for "✅ MongoDB connected")
- [ ] Redis is running (or confirmed to run in sync mode)
- [ ] Backend API is running on port 8000
- [ ] Celery worker is running (check for "Starting video processing task")
- [ ] Frontend is running on port 3000
- [ ] `.env` file exists with required API keys

Then:
1. Upload video or paste URL
2. Check backend logs for processing progress
3. Frontend should show progress updates
4. Clips appear when complete

---

## Quick Restart (if stuck)

```bash
# Kill all processes:
# Ctrl+C in each terminal

# Then restart in order:
# Terminal 1: redis-server
# Terminal 2: mongod
# Terminal 3: backend API
# Terminal 4: Celery worker
# Terminal 5: frontend
```

**Note**: The synchronous mode means if these steps don't work, you can still run with just the API (Terminal 3) - it will process synchronously without needing Celery/Redis.
