"""
Configuration for AI YouTube Shorts (content queue pipeline).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    if value is None:
        return default
    return value.strip().strip('"').strip("'")


# API Keys
GEMINI_API_KEY = _env("GEMINI_API_KEY", "")

# Paths
OUTPUT_FOLDER = _env("OUTPUT_FOLDER", "./output_reels")
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

# Short dimensions (9:16)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# YouTube API
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"

VIDEO_CATEGORIES = {
    "Film & Animation": 1, "Music": 10, "Pets & Animals": 15,
    "Sports": 17, "Gaming": 20, "People & Blogs": 22, "Comedy": 23,
    "Entertainment": 24, "News & Politics": 25, "Howto & Style": 26,
    "Education": 27, "Science & Technology": 28,
}

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
AUTO_UPLOAD = os.getenv("AUTO_UPLOAD", "false").lower() in ("1", "true", "yes")

# Niche context for Gemini when expanding a topic line
TIP_NICHE = _env("TIP_NICHE", "AI tools and productivity for beginners")
TTS_VOICE = _env("TTS_VOICE", "en-US-JennyNeural")

# Channel branding (slides)
CHANNEL_NAME = _env("CHANNEL_NAME", "Dailytix")
CHANNEL_CTA = _env("CHANNEL_CTA", "Follow Dailytix for daily tips")
TIP_BG_COLOR = _env("TIP_BG_COLOR", "#0A192F")
TIP_BRAND_COLOR = _env("TIP_BRAND_COLOR", "#FF8C00")
TIP_TEXT_COLOR = _env("TIP_TEXT_COLOR", "#FFFFFF")
TIP_BRAND_COLOR_2 = _env("TIP_BRAND_COLOR_2", "#FF8C00")
TIP_XFADE_DURATION = float(os.getenv("TIP_XFADE_DURATION", "0.3"))
TIP_FPS = int(os.getenv("TIP_FPS", "30"))
TIP_TOTAL_DURATION = float(os.getenv("TIP_TOTAL_DURATION", "28"))
_raw_durations = os.getenv("TIP_SLIDE_DURATIONS", "5.3,6.3,6.3,6.3,5.3")
TIP_SLIDE_DURATIONS = [float(x.strip()) for x in _raw_durations.split(",")]

def _resolve_channel_logo() -> str:
    """Prefer .env path, then project logo.png, then assets/."""
    candidates = [
        _env("CHANNEL_LOGO_PATH", ""),
        "./logo.png",
        "./assets/logo.png",
        "./assets/channel_logo.png",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return ""


CHANNEL_LOGO_PATH = _resolve_channel_logo()
BACKGROUND_MUSIC_PATH = _env("BACKGROUND_MUSIC_PATH", "./assets/background_music.mp3")

# Content queue: one topic per line → AI video
CONTENT_QUEUE_FILE = _env("CONTENT_QUEUE_FILE", "./content/video_topics.txt")
QUEUE_OUTPUT_FOLDER = _env("QUEUE_OUTPUT_FOLDER", os.path.join(OUTPUT_FOLDER, "queue"))

# Two runs per day (~12 hours apart)
_raw_time1 = os.getenv("UPLOAD_TIME_1", os.getenv("DAILY_UPLOAD_TIME", "09:00"))
UPLOAD_TIME_1 = "09:00"
if _raw_time1:
    parts = _raw_time1.strip().split(":")
    if len(parts) >= 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                UPLOAD_TIME_1 = f"{h:02d}:{m:02d}"
        except ValueError:
            pass

_raw_time2 = _env("UPLOAD_TIME_2", "21:00")
UPLOAD_TIME_2 = "21:00"
if _raw_time2:
    parts = _raw_time2.strip().split(":")
    if len(parts) >= 2:
        try:
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                UPLOAD_TIME_2 = f"{h:02d}:{m:02d}"
        except ValueError:
            pass
