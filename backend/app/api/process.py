from fastapi import APIRouter, HTTPException
from app.models.schemas import JobStatusResponse
from app.database.mongodb import get_db
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def _sanitize_job(job: dict) -> dict:
    """Remove non-serializable fields from MongoDB document."""
    if not job:
        return job
    job.pop("_id", None)
    # Convert datetime fields to ISO strings
    for key in ("created_at", "updated_at"):
        if key in job and job[key] is not None:
            job[key] = job[key].isoformat() if hasattr(job[key], "isoformat") else str(job[key])
    return job

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a processing job"""
    db = await get_db()
    job = await db.jobs.find_one({"job_id": job_id})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress", 0),
        clips=job.get("clips", []),
        error=job.get("error")
    )

@router.get("/jobs")
async def list_jobs(status: str = None, limit: int = 10):
    """List all jobs, optionally filtered by status"""
    db = await get_db()
    query = {}
    if status:
        query["status"] = status
    
    cursor = db.jobs.find(query).sort("created_at", -1).limit(limit)
    jobs = await cursor.to_list(length=limit)
    
    # Sanitize each job (remove ObjectId, convert datetimes)
    sanitized = [_sanitize_job(j) for j in jobs]
    
    return {"jobs": sanitized}

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated clip files"""
    db = await get_db()
    job = await db.jobs.find_one({"job_id": job_id})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete clip files from disk
    clips = job.get("clips", [])
    deleted_files = 0
    for clip in clips:
        clip_path = clip.get("video_path") or clip.get("path")
        if clip_path and os.path.exists(clip_path):
            try:
                os.remove(clip_path)
                deleted_files += 1
            except Exception as e:
                logger.warning(f"Failed to delete clip file {clip_path}: {e}")
    
    # Delete subtitle file if exists
    subtitle_path = None
    for clip in clips:
        sp = clip.get("subtitle_path")
        if sp:
            subtitle_path = sp
            break
    if subtitle_path and os.path.exists(subtitle_path):
        try:
            os.remove(subtitle_path)
        except Exception as e:
            logger.warning(f"Failed to delete subtitle file {subtitle_path}: {e}")
    
    # Delete job from database
    await db.jobs.delete_one({"job_id": job_id})
    
    logger.info(f"Deleted job {job_id} ({deleted_files} clip files removed)")
    return {"message": "Job deleted successfully", "job_id": job_id, "deleted_files": deleted_files}
