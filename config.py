"""
Configuration file for AI YouTube Automation
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
VIDEO_SOURCE_FOLDER = _env("VIDEO_SOURCE_FOLDER", "./downloaded_videos")
OUTPUT_FOLDER = _env("OUTPUT_FOLDER", "./output_reels")
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

# Video Processing
MAX_VIDEO_DURATION = int(os.getenv("MAX_VIDEO_DURATION", "300"))
TARGET_REEL_DURATION_MIN = 10
TARGET_REEL_DURATION_MAX = 15
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# YouTube Settings
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

# When true, "run" / "process" / scheduler upload reels after creating them
AUTO_UPLOAD = os.getenv("AUTO_UPLOAD", "false").lower() in ("1", "true", "yes")

# Validate and normalize DAILY_UPLOAD_TIME to strict "HH:MM" format
_raw_time = os.getenv("DAILY_UPLOAD_TIME", "09:00")
DAILY_UPLOAD_TIME = "09:00"  # default fallback
if _raw_time:
    # Remove common suffixes like " AM", " PM"
    clean_time = _raw_time.strip().upper().replace(" AM", "").replace(" PM", "")
    parts = clean_time.split(":")
    if len(parts) >= 2:
        try:
            hour = int(parts[0])
            minute = int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                DAILY_UPLOAD_TIME = f"{hour:02d}:{minute:02d}"
        except ValueError:
            pass
    if DAILY_UPLOAD_TIME == "09:00" and _raw_time != "09:00":
        print(f"[config] Warning: Invalid DAILY_UPLOAD_TIME '{_raw_time}', using default '09:00'")

# Idea 2: Daily original English tip Shorts (faceless + TTS)
TIP_NICHE = _env("TIP_NICHE", "AI tools and productivity for beginners")
TIPS_OUTPUT_FOLDER = _env("TIPS_OUTPUT_FOLDER", os.path.join(OUTPUT_FOLDER, "tips"))
TTS_VOICE = _env("TTS_VOICE", "en-US-JennyNeural")

# Channel branding (shown on every slide)
CHANNEL_NAME = _env("CHANNEL_NAME", "Dailytix")
CHANNEL_CTA = _env("CHANNEL_CTA", "Follow Dailytix for daily tips")
TIP_BG_COLOR = _env("TIP_BG_COLOR", "#0A192F")
TIP_BRAND_COLOR = _env("TIP_BRAND_COLOR", "#FF8C00")
TIP_TEXT_COLOR = _env("TIP_TEXT_COLOR", "#FFFFFF")
TIP_BRAND_COLOR_2 = _env("TIP_BRAND_COLOR_2", "#FF8C00")
TIP_XFADE_DURATION = float(os.getenv("TIP_XFADE_DURATION", "0.3"))
TIP_FPS = int(os.getenv("TIP_FPS", "30"))
TIP_TOTAL_DURATION = float(os.getenv("TIP_TOTAL_DURATION", "28"))
# Base 5+6+6+6+5=28s + 0.3s per xfade overlap → segment lengths below
_raw_durations = os.getenv("TIP_SLIDE_DURATIONS", "5.3,6.3,6.3,6.3,5.3")
TIP_SLIDE_DURATIONS = [float(x.strip()) for x in _raw_durations.split(",")]

# Optional: assets/channel_logo.png (square PNG) and assets/background_music.mp3
CHANNEL_LOGO_PATH = _env("CHANNEL_LOGO_PATH", "./assets/channel_logo.png")
BACKGROUND_MUSIC_PATH = _env("BACKGROUND_MUSIC_PATH", "./assets/background_music.mp3")