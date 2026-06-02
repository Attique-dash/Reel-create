from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobRequest(BaseModel):
    url: Optional[str] = None
    num_clips: int = Field(default=5, ge=1, le=20)
    clip_duration: int = Field(default=60, ge=15, le=180)
    aspect_ratio: str = Field(default="9:16", pattern=r"^(9:16|1:1|16:9)$")
    subtitle_style: dict = Field(default_factory=lambda: {
        "font": "Arial",
        "size": 24,
        "color": "white",
        "position": "bottom"
    })

class Clip(BaseModel):
    id: str
    start_time: float
    end_time: float
    duration: float
    subtitle_path: Optional[str] = None
    video_path: Optional[str] = None
    tags: List[str] = []
    engagement_score: float = 0.0

class Job(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    video_path: Optional[str] = None
    clips: List[Clip] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    settings: JobRequest

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float
    clips: List[Clip] = []
    error: Optional[str] = None
