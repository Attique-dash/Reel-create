from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

PROCESSED_DIR = os.getenv("PROCESSED_DIR", "./storage/processed")


async def _find_clip_path(clip_id: str) -> str | None:
    """Find the actual file path for a clip by searching jobs in the database."""
    from app.database.mongodb import database

    # Search for a job that contains this clip_id in its clips array
    job = await database.jobs.find_one({"clips.id": clip_id})
    if not job:
        return None

    for clip in job.get("clips", []):
        if clip.get("id") == clip_id:
            path = clip.get("video_path") or clip.get("path")
            if path and os.path.exists(path):
                return path
    return None


@router.get("/clip/{clip_id}")
async def download_clip(clip_id: str):
    """Download a specific clip by ID"""
    clip_path = await _find_clip_path(clip_id)

    if not clip_path:
        # Fallback: try direct file lookup
        direct_path = os.path.join(PROCESSED_DIR, f"{clip_id}.mp4")
        if os.path.exists(direct_path):
            clip_path = direct_path

    if not clip_path or not os.path.exists(clip_path):
        logger.error(f"Clip not found: {clip_id}")
        raise HTTPException(status_code=404, detail="Clip not found")

    filename = os.path.basename(clip_path)
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get("/preview/{clip_id}")
async def preview_clip(clip_id: str):
    """Stream clip preview (inline, for <video> elements)"""
    clip_path = await _find_clip_path(clip_id)

    if not clip_path:
        direct_path = os.path.join(PROCESSED_DIR, f"{clip_id}.mp4")
        if os.path.exists(direct_path):
            clip_path = direct_path

    if not clip_path or not os.path.exists(clip_path):
        logger.error(f"Clip not found for preview: {clip_id}")
        raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(
        clip_path,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )


@router.get("/job/{job_id}")
async def download_all_clips(job_id: str):
    """Download all clips for a job as a zip file"""
    import zipfile
    import io
    from app.database.mongodb import JobRepository

    job = await JobRepository.get_job(job_id)

    if not job:
        logger.error(f"Job not found: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")

    clips = job.get("clips", [])

    if not clips:
        logger.error(f"No clips found for job: {job_id}")
        raise HTTPException(status_code=404, detail="No clips found for this job")

    zip_buffer = io.BytesIO()
    added_count = 0

    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
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
            headers={"Content-Disposition": f"attachment; filename=clips_{job_id}.zip"},
        )

    except Exception as e:
        logger.error(f"Error creating zip file for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating zip file")
