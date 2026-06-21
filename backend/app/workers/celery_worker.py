from celery import Celery
import os
import asyncio
import logging
from datetime import datetime
import redis
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

# Thread pool executor for running async functions from sync context
_executor = ThreadPoolExecutor(max_workers=4)

def run_async(coro):
    """Run async function from sync context, handling if event loop already exists"""
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, we can use asyncio.run()
        return asyncio.run(coro)
    else:
        # There's already a running loop, use thread pool
        import concurrent.futures
        future = _executor.submit(asyncio.run, coro)
        return future.result()

# Check if Redis is actually available
def is_redis_available():
    """Check if Redis broker is actually running"""
    try:
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        # Parse Redis URL
        if redis_url.startswith("redis://"):
            redis_url = redis_url.replace("redis://", "")
        host, port = redis_url.split(":") if ":" in redis_url else (redis_url, 6379)
        port = int(port.split("/")[0])
        
        # Test actual connection
        r = redis.Redis(
            host=host, 
            port=port, 
            socket_connect_timeout=1,
            socket_keepalive=False,
            health_check_interval=0
        )
        r.ping()
        return True
    except Exception as e:
        return False

# Determine processing mode
REDIS_AVAILABLE = is_redis_available()
FORCE_SYNC = os.getenv("FORCE_SYNC", "true").lower() == "true"
USE_ASYNC = REDIS_AVAILABLE and not FORCE_SYNC

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
    task_always_eager=not USE_ASYNC,  # Use synchronous mode by default for development
    task_eager_propagates=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
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
    logger.info(f"🔵 Starting video processing task for job_id: {job_id} (source_type: {source_type})")
    
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
        logger.info(f"✅ Job {job_id}: All dependencies loaded successfully")
    except ImportError as e:
        error_msg = f"Video processing dependencies not installed: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}")
        run_async(update_job_status(job_id, "failed", 0, error=error_msg))
        return {"status": "failed", "job_id": job_id, "error": error_msg}
    
    try:
        # Update job status to processing
        logger.info(f"📝 Job {job_id}: Updating status to 'processing'")
        run_async(update_job_status(job_id, "processing", 10))
        logger.info(f"✅ Job {job_id}: Status updated to processing")
        
        # Step 1: Download or validate video
        logger.info(f"📥 Job {job_id}: Step 1/6 - Getting video source (type: {source_type})")
        if source_type == "url":
            logger.info(f"🌐 Job {job_id}: Downloading video from URL: {video_source}")
            video_path = download_video(video_source)
            logger.info(f"✅ Job {job_id}: Video downloaded to {video_path}")
        else:
            video_path = video_source
            logger.info(f"📂 Job {job_id}: Using local file: {video_path}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
        logger.info(f"✅ Job {job_id}: Video file ready ({file_size:.2f} MB)")
        run_async(update_job_status(job_id, "processing", 20))
        
        # Step 2: Transcribe video
        logger.info(f"🎤 Job {job_id}: Step 2/6 - Transcribing video")
        transcript = transcribe_video(video_path)
        video_duration = transcript.get('duration', 0)
        segments_count = len(transcript.get('segments', []))
        logger.info(f"✅ Job {job_id}: Transcription completed (duration: {video_duration:.1f}s, segments: {segments_count})")
        
        run_async(update_job_status(job_id, "processing", 40))
        
        # Step 3: AI analysis for best moments
        logger.info(f"🤖 Job {job_id}: Step 3/6 - Analyzing moments with AI")
        moments = analyze_moments(transcript, merged_settings)
        logger.info(f"✅ Job {job_id}: Found {len(moments)} engaging moments for clipping")
        
        run_async(update_job_status(job_id, "processing", 60))
        
        # Step 4: Create clips
        logger.info(f"✂️ Job {job_id}: Step 4/6 - Creating {len(moments)} clips")
        clips = create_clips(video_path, moments, merged_settings, video_duration=video_duration)
        logger.info(f"✅ Job {job_id}: Successfully created {len(clips)} clips")
        
        run_async(update_job_status(job_id, "processing", 75))
        
        # Step 5: Smart crop (optional, don't fail on error)
        logger.info(f"📐 Job {job_id}: Step 5/6 - Applying smart crop to clips")
        try:
            cropped_count = 0
            for i, clip in enumerate(clips):
                try:
                    clip_path = clip.get("video_path") or clip.get("path")
                    if clip_path and os.path.exists(clip_path):
                        smart_crop_video(clip_path, merged_settings)
                        cropped_count += 1
                        logger.debug(f"Job {job_id}: Smart crop applied to clip {i}/{len(clips)}")
                except Exception as e:
                    logger.warning(f"Job {job_id}: Smart crop failed for clip {i}: {str(e)}, continuing...")
            logger.info(f"✅ Job {job_id}: Smart crop applied to {cropped_count}/{len(clips)} clips")
        except Exception as e:
            logger.warning(f"⚠️ Job {job_id}: Smart crop step had issues: {str(e)}, but clips are still valid")
        
        run_async(update_job_status(job_id, "processing", 90))
        
        # Step 6: Update job status to completed
        logger.info(f"✅ Job {job_id}: Step 6/6 - Finalizing job status")
        run_async(update_job_status(job_id, "completed", 100, clips=clips))
        logger.info(f"🎉 Job {job_id}: Processing completed successfully! Generated {len(clips)} clips")
        
        return {"status": "completed", "job_id": job_id, "clips_count": len(clips)}
    
    except Exception as e:
        error_msg = f"Video processing failed: {str(e)}"
        logger.error(f"❌ Job {job_id}: {error_msg}", exc_info=True)
        run_async(update_job_status(job_id, "failed", 0, error=error_msg))
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
