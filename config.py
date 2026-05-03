"""
Configuration file for AI YouTube Automation
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Paths
VIDEO_SOURCE_FOLDER = os.getenv("VIDEO_SOURCE_FOLDER", "./downloaded_videos")
OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", "./output_reels")
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

# Video Processing
MAX_VIDEO_DURATION = int(os.getenv("MAX_VIDEO_DURATION", "300"))  # 5 minutes max for source
TARGET_REEL_DURATION_MIN = 15  # seconds
TARGET_REEL_DURATION_MAX = 60  # seconds
VIDEO_WIDTH = 1080  # Vertical video width
VIDEO_HEIGHT = 1920  # Vertical video height (9:16 aspect ratio)

# YouTube Settings
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"

# Categories mapping
VIDEO_CATEGORIES = {
    "Film & Animation": 1,
    "Autos & Vehicles": 2,
    "Music": 10,
    "Pets & Animals": 15,
    "Sports": 17,
    "Travel & Events": 19,
    "Gaming": 20,
    "People & Blogs": 22,
    "Comedy": 23,
    "Entertainment": 24,
    "News & Politics": 25,
    "Howto & Style": 26,
    "Education": 27,
    "Science & Technology": 28,
    "Nonprofits & Activism": 29
}

# Gemini Model
GEMINI_MODEL = "gemini-1.5-flash"  # Free tier model

# Scheduler Settings
DAILY_UPLOAD_TIME = os.getenv("DAILY_UPLOAD_TIME", "09:00")
