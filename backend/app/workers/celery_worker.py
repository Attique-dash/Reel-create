from celery import Celery
import os
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

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

# Default settings
DEFAULT_SETTINGS = {
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

@celery_app.task(bind=True, max_retries=3)
def process_video_task(self, job_id: str, video_source: str, source_type: str, settings: dict = None):
    """Background task to process video with comprehensive error handling"""
    logger.info(f"Starting video processing task for job_id: {job_id}")
    
    # Merge settings with defaults
    if settings is None:
        settings = {}
    merged_settings = {**DEFAULT_SETTINGS, **settings}
    
    try:
        from app.services.video_downloader import download_video
        from app.services.transcriber import transcribe_video
        from app.services.ai_analyzer import analyze_moments
        from app.services.video_editor import create_clips
        from app.services.smart_crop import smart_crop_video
    except ImportError as e:
        error_msg = f"Video processing dependencies not installed: {str(e)}"
        logger.error(error_msg)
        asyncio.run(update_job_status(job_id, "failed", 0, error=error_msg))
        return {"status": "failed", "job_id": job_id, "error": error_msg}
    
    try:
        # Update job status to processing
        asyncio.run(update_job_status(job_id, "processing", 10))
        logger.info(f"Job {job_id}: Status updated to processing")
        
        # Step 1: Download or validate video
        logger.info(f"Job {job_id}: Step 1 - Getting video source (type: {source_type})")
        if source_type == "url":
            video_path = download_video(video_source)
        else:
            video_path = video_source
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        asyncio.run(update_job_status(job_id, "processing", 30))
        logger.info(f"Job {job_id}: Video source ready - {video_path}")
        
        # Step 2: Transcribe video
        logger.info(f"Job {job_id}: Step 2 - Transcribing video")
        transcript = transcribe_video(video_path)
        video_duration = transcript.get('duration', 0)
        logger.info(f"Job {job_id}: Transcription completed (duration: {video_duration:.1f}s, segments: {len(transcript.get('segments', []))}")
        
        asyncio.run(update_job_status(job_id, "processing", 50))
        
        # Step 3: AI analysis for best moments
        logger.info(f"Job {job_id}: Step 3 - Analyzing moments with AI")
        moments = analyze_moments(transcript, merged_settings)
        logger.info(f"Job {job_id}: Found {len(moments)} moments for clipping")
        
        asyncio.run(update_job_status(job_id, "processing", 70))
        
        # Step 4: Create clips
        logger.info(f"Job {job_id}: Step 4 - Creating clips")
        clips = create_clips(video_path, moments, merged_settings, video_duration=video_duration)
        logger.info(f"Job {job_id}: Successfully created {len(clips)} clips")
        
        asyncio.run(update_job_status(job_id, "processing", 85))
        
        # Step 5: Smart crop (optional, don't fail on error)
        logger.info(f"Job {job_id}: Step 5 - Applying smart crop")
        try:
            for i, clip in enumerate(clips):
                try:
                    clip_path = clip.get("video_path") or clip.get("path")
                    if clip_path and os.path.exists(clip_path):
                        smart_crop_video(clip_path, merged_settings)
                        logger.info(f"Job {job_id}: Smart crop applied to clip {i}")
                except Exception as e:
                    logger.warning(f"Job {job_id}: Smart crop failed for clip {i}: {str(e)}, continuing...")
        except Exception as e:
            logger.warning(f"Job {job_id}: Smart crop step failed: {str(e)}, but clips are still valid")
        
        asyncio.run(update_job_status(job_id, "processing", 95))
        
        # Step 6: Update job status to completed
        logger.info(f"Job {job_id}: Finalizing job status")
        asyncio.run(update_job_status(job_id, "completed", 100, clips=clips))
        logger.info(f"Job {job_id}: Processing completed successfully")
        
        return {"status": "completed", "job_id": job_id, "clips_count": len(clips)}
    
    except Exception as e:
        error_msg = f"Video processing failed: {str(e)}"
        logger.error(f"Job {job_id}: {error_msg}", exc_info=True)
        asyncio.run(update_job_status(job_id, "failed", 0, error=error_msg))
        return {"status": "failed", "job_id": job_id, "error": error_msg}

async def update_job_status(job_id: str, status: str, progress: int, clips: list = None, error: str = None):
    """Update job status in database with proper formatting"""
    from app.database.mongodb import JobRepository
    
    update_data = {
        "status": status,
        "progress": progress
    }
    
    if clips is not None:
        # Ensure clips are in proper format
        formatted_clips = []
        for clip in clips:
            formatted_clip = {
                "id": clip.get("id", ""),
                "start_time": float(clip.get("start_time", 0)),
                "end_time": float(clip.get("end_time", 0)),
                "duration": float(clip.get("duration", 0)),
                "subtitle_path": clip.get("subtitle_path"),
                "video_path": clip.get("video_path") or clip.get("path"),
                "tags": clip.get("tags", []),
                "engagement_score": float(clip.get("engagement_score", 0))
            }
            formatted_clips.append(formatted_clip)
        update_data["clips"] = formatted_clips
    
    if error:
        update_data["error"] = error
    
    await JobRepository.update_job(job_id, **update_data)
