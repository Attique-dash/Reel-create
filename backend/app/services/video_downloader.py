import yt_dlp
import os

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./storage/uploads")

def download_video(url: str) -> str:
    """Download video from URL using yt-dlp"""
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': os.path.join(UPLOAD_DIR, '%(id)s.%(ext)s'),
        'quiet': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.join(UPLOAD_DIR, f"{info['id']}.{info['ext']}")
