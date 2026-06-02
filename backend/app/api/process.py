from fastapi import APIRouter, HTTPException
from app.models.schemas import JobStatusResponse
from app.database.mongodb import get_db

router = APIRouter()

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
    
    return {"jobs": jobs}
