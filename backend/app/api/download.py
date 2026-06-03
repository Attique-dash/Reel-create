from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()

PROCESSED_DIR = os.getenv("PROCESSED_DIR", "./storage/processed")

@router.get("/preview/{clip_id}")
async def preview_clip(clip_id: str):
    """Stream clip preview"""
    clip_path = os.path.join(PROCESSED_DIR, f"{clip_id}.mp4")
    
    if not os.path.exists(clip_path):
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
    
    job_dir = os.path.join(PROCESSED_DIR, job_id)
    
    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job clips not found")
    
    # Create zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename in os.listdir(job_dir):
            if filename.endswith('.mp4'):
                file_path = os.path.join(job_dir, filename)
                zip_file.write(file_path, filename)
    
    zip_buffer.seek(0)
    
    from fastapi.responses import Response
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={job_id}_clips.zip"}
    )
