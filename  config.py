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
DAILY_UPLOAD_TIME = os.getenv("DAILY_UPLOAD_TIME", "09:00")