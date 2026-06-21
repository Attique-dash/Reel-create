# MongoDB Atlas Connection Guide

## Current Setup

Your backend is now configured to use **MongoDB Atlas** (Cloud) instead of local MongoDB.

**Configuration**: 
- Connection String: `mongodb+srv://atti_projects:FKS4m62ZAnLJvUMt@shorts.uyam71o.mongodb.net/video_processor`
- Database: `video_processor`

---

## ✅ How to Get Your Backend Running

### Step 1: Stop the Current Backend
```bash
# Press Ctrl+C in the terminal where uvicorn is running
```

### Step 2: Restart Backend with New Configuration
```bash
cd /Users/apple/Desktop/AI-Automation/backend
source venv/bin/activate

# Option A: Use the new startup script (Recommended)
chmod +x start_backend.sh
./start_backend.sh

# Option B: Run directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Verify Connection
You should see:
```
✅ MongoDB connection successful!
📦 Using database: video_processor
📑 Database indexes created
🎬 VIDEO PROCESSOR API STARTED
```

---

## 🔍 Troubleshooting MongoDB Atlas Connection

### Error: "Connection refused" or "Connection timed out"

**Check 1: Internet Connection**
```bash
# Make sure you have internet access
ping 8.8.8.8
```

**Check 2: MongoDB Atlas IP Whitelist**
1. Go to: https://cloud.mongodb.com/
2. Click "Security" → "Network Access"
3. Add your current IP address (or 0.0.0.0/0 for all)
4. Your IP might be shown when you get the error

**Check 3: Connection String**
- Make sure your MONGODB_URI in .env has:
  - Correct username: `atti_projects`
  - Correct password: `FKS4m62ZAnLJvUMt`
  - Cluster name: `shorts`

### Error: "authentication failed"

**Solution:**
1. Go to: https://cloud.mongodb.com/
2. Click "Database Access"
3. Verify the password for user `atti_projects`
4. If special characters in password, they might need escaping in the URI

### Error: "MongoServerError: user is not allowed to perform"

**Solution:**
1. Go to: https://cloud.mongodb.com/
2. Click "Database Access"  
3. Give user `atti_projects` the role: "Atlas Admin" or at least "readWrite"

---

## 🔧 Quick Connection Test

To manually test the MongoDB connection:

```bash
cd backend
source venv/bin/activate
python
```

Then paste this:
```python
import asyncio
from app.database.mongodb import init_db, get_db, JobRepository

async def test():
    await init_db()
    db = await get_db()
    
    # Try to list collections
    collections = await db.list_collection_names()
    print("Collections:", collections)
    
    # Try to get a job (if any exist)
    jobs = await JobRepository.list_jobs(limit=1)
    print("Jobs:", jobs)

asyncio.run(test())
```

Should output without errors if connection is working.

---

## 📊 MongoDB Atlas Dashboard

To monitor your data:

1. Go to: https://cloud.mongodb.com/
2. Click "Browse Collections"
3. You'll see:
   - Database: `video_processor`
   - Collections: `jobs` (where processing jobs are stored)

---

## ⚠️ Security Note

⚠️ **IMPORTANT**: Your MongoDB Atlas credentials are now in `.env` file in your project directory.

### To Secure Your Credentials:

1. **Never commit `.env` to Git**:
   ```bash
   # Make sure .gitignore includes .env
   echo ".env" >> .gitignore
   ```

2. **Rotate Your Password** (Recommended):
   - Go to: https://cloud.mongodb.com/
   - Click "Database Access"
   - Edit user `atti_projects`
   - Change password to a new secure one
   - Update the new password in `.env`

3. **Use Environment Variables in Production**:
   - Don't hardcode credentials in files
   - Use Docker secrets or environment variable services

---

## 🚀 Next: Start Backend

```bash
cd /Users/apple/Desktop/AI-Automation/backend
chmod +x start_backend.sh
./start_backend.sh
```

You should now see:
```
✅ MongoDB connected successfully to video_processor
🎬 VIDEO PROCESSOR API STARTED
📊 Frontend: http://localhost:3000
🔌 API: http://localhost:8000
📚 Docs: http://localhost:8000/docs
```

---

## 📚 Next Steps After Backend Starts

1. **Start Redis** (for task queue):
   ```bash
   redis-server
   ```

2. **Start Celery Worker** (in another terminal):
   ```bash
   cd backend
   source venv/bin/activate
   chmod +x start_celery_worker.sh
   ./start_celery_worker.sh
   ```

3. **Start Frontend** (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```

4. **Test**: Upload a video at http://localhost:3000

---

## ✅ Checklist

Before uploading videos, verify:

- [ ] Backend shows "✅ MongoDB connected successfully"
- [ ] Backend shows "🎬 VIDEO PROCESSOR API STARTED"
- [ ] API accessible at http://localhost:8000/docs
- [ ] Frontend running at http://localhost:3000
- [ ] Redis running (if available - not required for development)
- [ ] Celery worker running (if available - not required for development)

---

## 💾 Your Configuration

```
Location: /Users/apple/Desktop/AI-Automation/backend/.env

Key Values:
- MongoDB: MongoDB Atlas (Cloud-hosted)
- Database: video_processor
- API Key: Gemini configured
- Storage: Local directories in ./storage/
- Frontend URL: http://localhost:8000
```

---

**Ready to get processing videos!** 🎬✨
