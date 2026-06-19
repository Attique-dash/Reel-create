from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uuid
import os
import aiofiles
from app.models.schemas import UploadResponse, JobRequest, Job, JobStatus
from app.workers.celery_worker import process_video_task
from app.database.mongodb import JobRepository

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./storage/uploads")

@router.post("/", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file for processing"""
    job_id = str(uuid.uuid4())
    
    # Create upload directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Default settings for file upload
    default_settings = {
        "num_clips": 5,
        "clip_duration": 60,
        "aspect_ratio": "9:16",
        "subtitle_style": {
            "font": "Arial",
            "size": 24,
            "color": "white",
            "position": "bottom"
        }
    }
    
    # Save job to database with default settings
    await JobRepository.create_job(job_id, source_type="file", source_path=file_path, settings=default_settings)
    
    # Trigger background processing with settings
    process_video_task.delay(job_id, file_path, "file", default_settings)
    
    return UploadResponse(
        job_id=job_id,
        status="pending",
        message="Video uploaded successfully. Processing started."
    )

@router.post("/url", response_model=UploadResponse)
async def upload_video_url(request: JobRequest):
    """Submit a video URL for processing"""
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    job_id = str(uuid.uuid4())
    
    # Save job to database
    await JobRepository.create_job(job_id, source_type="url", source_path=request.url, settings=request.dict())
    
    # Trigger background processing
    process_video_task.delay(job_id, request.url, "url", request.dict())
    
    return UploadResponse(
        job_id=job_id,
        status="pending",
        message="Video URL submitted. Processing started."
    )
