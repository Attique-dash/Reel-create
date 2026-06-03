#!/bin/bash
source venv/bin/activate
pip install --upgrade pip
pip install opencv-python==4.8.1.78
pip install opencv-contrib-python==4.8.1.78
pip install faster-whisper
pip install google-genai
pip install mediapipe
pip install fastapi uvicorn celery redis motor pydantic-settings
pip install yt-dlp ffmpeg-python aiofiles
echo "All packages installed successfully!"
