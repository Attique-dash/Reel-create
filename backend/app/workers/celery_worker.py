from celery import Celery
import os
from datetime import datetime

# Celery configuration
celery_app = Celery(
    "video_processor",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(bind=True)
def process_video_task(self, job_id: str, video_source: str, source_type: str, settings: dict = None):
    """Background task to process video"""
    try:
        from app.services.video_downloader import download_video
        from app.services.transcriber import transcribe_video
        from app.services.ai_analyzer import analyze_moments
        from app.services.video_editor import create_clips
        from app.services.smart_crop import smart_crop_video
    except ImportError as e:
        asyncio.run(update_job_status(job_id, "failed", 0, error=f"Video processing dependencies not installed: {str(e)}"))
        return {"status": "failed", "job_id": job_id, "error": f"Missing dependencies: {str(e)}"}
    
    from app.database.mongodb import get_db
    import asyncio
    
    try:
        # Update job status to processing
        asyncio.run(update_job_status(job_id, "processing", 10))
        
        # Step 1: Download video if URL
        if source_type == "url":
            video_path = download_video(video_source)
        else:
            video_path = video_source
        
        asyncio.run(update_job_status(job_id, "processing", 30))
        
        # Step 2: Transcribe video
        transcript = transcribe_video(video_path)
        asyncio.run(update_job_status(job_id, "processing", 50))
        
        # Step 3: AI analysis for best moments
        moments = analyze_moments(transcript, settings)
        asyncio.run(update_job_status(job_id, "processing", 70))
        
        # Step 4: Create clips
        clips = create_clips(video_path, moments, settings)
        asyncio.run(update_job_status(job_id, "processing", 85))
        
        # Step 5: Smart crop and subtitle burning
        for clip in clips:
            smart_crop_video(clip["path"], settings)
        
        # Update job status to completed
        asyncio.run(update_job_status(job_id, "completed", 100, clips))
        
        return {"status": "completed", "job_id": job_id}
    
    except Exception as e:
        asyncio.run(update_job_status(job_id, "failed", 0, error=str(e)))
        raise e

async def update_job_status(job_id: str, status: str, progress: int, clips: list = None, error: str = None):
    """Update job status in database"""
    from app.database.sqlite_adapter import JobRepository
    update_data = {
        "status": status,
        "progress": progress
    }
    
    if clips:
        update_data["clips"] = clips
    
    if error:
        update_data["error"] = error
    
    await JobRepository.update_job(job_id, **update_data)
