from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload, process, download
from app.database.mongodb import init_db
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Video Processor API",
    description="AI-powered video processing pipeline for short content creation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(process.router, prefix="/api/process", tags=["process"])
app.include_router(download.router, prefix="/api/download", tags=["download"])

@app.on_event("startup")
async def startup_event():
    await init_db()
    print("Video Processor API started")

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
