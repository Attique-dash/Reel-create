from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload, process, download
from app.database.mongodb import init_db
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Processor API",
    description="AI-powered video processing pipeline for short content creation",
    version="1.0.0"
)

# CORS middleware - Must be added FIRST (before other middleware)
# In FastAPI, middleware is added in reverse order, so this needs to be first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(process.router, prefix="/api/process", tags=["process"])
app.include_router(download.router, prefix="/api/download", tags=["download"])

@app.on_event("startup")
async def startup_event():
    await init_db()
    
    # Check Celery configuration
    from app.workers.celery_worker import celery_app, USE_ASYNC, REDIS_AVAILABLE
    
    print("\n" + "="*60)
    print("🎬 VIDEO PROCESSOR API STARTED")
    print("="*60)
    print(f"📊 Frontend: http://localhost:3000")
    print(f"🔌 API: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    print("="*60)
    
    if USE_ASYNC:
        print("⚠️  CELERY RUNNING IN ASYNC MODE")
        print("   Make sure Celery worker is started:")
        print("   cd backend && ./start_celery_worker.sh")
        logger.info("✅ CELERY CONFIGURED FOR ASYNC PROCESSING (Redis available)")
    else:
        print("✅ CELERY RUNNING IN SYNCHRONOUS MODE")
        print("   Processing will happen immediately (no separate worker needed)")
        if REDIS_AVAILABLE:
            logger.info("ℹ️  Redis available but FORCE_SYNC=true in .env")
        else:
            logger.info("✅ CELERY RUNNING IN SYNCHRONOUS MODE (Redis not available)")
    
    print("="*60 + "\n")

@app.get("/")
async def root():
    return {
        "message": "Video Processor API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
