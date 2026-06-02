import ffmpeg
import os

PROCESSED_DIR = os.getenv("PROCESSED_DIR", "./storage/processed")

def create_clips(video_path: str, moments: list, settings: dict) -> list:
    """Create video clips using FFmpeg"""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    clips = []
    for i, moment in enumerate(moments):
        output_path = os.path.join(PROCESSED_DIR, f"clip_{i}.mp4")
        
        (
            ffmpeg
            .input(video_path, ss=moment['start_time'], t=moment['end_time'] - moment['start_time'])
            .output(output_path, c='copy')
            .overwrite_output()
            .run(quiet=True)
        )
        
        clips.append({
            "id": f"clip_{i}",
            "path": output_path,
            "start_time": moment['start_time'],
            "end_time": moment['end_time'],
            "engagement_score": moment['engagement_score']
        })
    
    return clips
