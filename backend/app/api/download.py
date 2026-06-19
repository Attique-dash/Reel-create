from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

PROCESSED_DIR = os.getenv("PROCESSED_DIR", "./storage/processed")

@router.get("/clip/{clip_id}")
async def download_clip(clip_id: str):
    """Download a specific clip by ID"""
    # Search for clip file
    clip_filename = f"clip_{clip_id}.mp4"
    clip_path = os.path.join(PROCESSED_DIR, clip_filename)
    
    if not os.path.exists(clip_path):
        logger.error(f"Clip not found: {clip_path}")
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"attachment; filename={clip_filename}"
        }
    )

@router.get("/preview/{clip_id}")
async def preview_clip(clip_id: str):
    """Stream clip preview (inline)"""
    clip_filename = f"clip_{clip_id}.mp4"
    clip_path = os.path.join(PROCESSED_DIR, clip_filename)
    
    if not os.path.exists(clip_path):
        logger.error(f"Clip not found for preview: {clip_path}")
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"}
    )

@router.get("/job/{job_id}")
async def download_all_clips(job_id: str):
    """Download all clips for a job as a zip file"""
    import zipfile
    import io
    from app.database.mongodb import JobRepository
    
    # Get job from database to find clips
    job = await JobRepository.get_job(job_id)
    
    if not job:
        logger.error(f"Job not found: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    clips = job.get("clips", [])
    
    if not clips:
        logger.error(f"No clips found for job: {job_id}")
        raise HTTPException(status_code=404, detail="No clips found for this job")
    
    # Create zip file in memory
    zip_buffer = io.BytesIO()
    added_count = 0
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, clip in enumerate(clips):
                clip_path = clip.get("video_path") or clip.get("path")
                
                if clip_path and os.path.exists(clip_path):
                    filename = os.path.basename(clip_path)
                    zip_file.write(clip_path, filename)
                    added_count += 1
                else:
                    logger.warning(f"Clip file not found for job {job_id}: {clip_path}")
        
        if added_count == 0:
            logger.error(f"No valid clip files found for job: {job_id}")
            raise HTTPException(status_code=404, detail="No valid clip files found")
        
        zip_buffer.seek(0)
        logger.info(f"Created zip archive for job {job_id} with {added_count} clips")
        
        from fastapi.responses import Response
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=clips_{job_id}.zip"}
        )
    
    except Exception as e:
        logger.error(f"Error creating zip file for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating zip file")
