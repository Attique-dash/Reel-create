# AI YouTube Automation

An automated pipeline that downloads trending videos, analyzes them with Google Gemini AI, creates vertical YouTube Shorts (reels), and uploads them to YouTube.

## Features

- **Video Discovery**: Search and download trending videos from YouTube
- **AI Analysis**: Uses Google Gemini to analyze content and suggest titles, descriptions, and key moments
- **Auto Editing**: Creates vertical 9:16 reels using ffmpeg (no MoviePy dependencies)
- **YouTube Upload**: Automated upload to YouTube with OAuth2 authentication
- **Scheduling**: Daily scheduled runs to keep content flowing
- **Deduplication**: Tracks processed videos to avoid creating duplicates

## Requirements

- Python 3.11+
- ffmpeg (with ffprobe)
- Google API credentials
- YouTube OAuth2 credentials

## Quick Start

### 1. Clone and Install

```bash
git clone <repo-url>
cd AI-Automation
pip install -r requirements.txt
```

### 2. Install ffmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description | How to Get |
|----------|-------------|------------|
| `GEMINI_API_KEY` | Google Gemini API key | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| `YOUTUBE_CLIENT_SECRETS_FILE` | Path to client_secrets.json | [Google Cloud Console](#youtube-oauth-setup) |

Optional variables:
- `VIDEO_SOURCE_FOLDER` - Where to save downloaded videos (default: `./downloaded_videos`)
- `OUTPUT_FOLDER` - Where to save created reels (default: `./output_reels`)
- `MAX_VIDEO_DURATION` - Max seconds to download (default: `300`)
- `DAILY_UPLOAD_TIME` - Time for scheduled runs (default: `09:00`)
- `GEMINI_MODEL` - Gemini model to use (default: `gemini-2.0-flash-lite`)

### 4. YouTube OAuth Setup

To upload to YouTube, you need OAuth2 credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **YouTube Data API v3**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Select **Desktop app** as the application type
6. Download the JSON file and rename it to `client_secrets.json` in the project root

**First-time authentication:**
```bash
python main.py test
```

This will open a browser window for you to authorize the app. The token will be saved to `youtube_token.pickle` for future runs.

## Usage

### Commands

```bash
# Test setup and connectivity
python main.py test

# Download trending videos
python main.py download --query "viral shorts" --max 3

# Analyze a specific video
python main.py analyze --video ./downloaded_videos/some_video.mp4

# Create preview reel (single reel with analysis)
python main.py preview --video ./downloaded_videos/some_video.mp4

# Create multiple reels from a video
python main.py create --video ./downloaded_videos/some_video.mp4

# Upload a reel to YouTube
python main.py upload --video ./output_reels/reel_some_video_part1.mp4 --privacy private

# Full pipeline: download, analyze, create reels, upload
python main.py run --privacy private

# Start daily scheduler
python main.py schedule --time "09:00"
```

### Idea 2 — Daily original tip Shorts (faceless + English TTS)

Creates **original** content: Gemini writes a tip script → `edge-tts` voiceover → PIL slides → 9:16 MP4. No downloading other creators' videos.

```bash
# 1. Install new dependency
pip install -r requirements.txt

# 2. Set niche in .env (optional)
# TIP_NICHE=AI tools and productivity for beginners
# TTS_VOICE=en-US-JennyNeural

# 3. Create today's Short locally (no YouTube)
python main.py daily-tip --no-upload

# 4. Upload to YouTube (private by default)
python main.py daily-tip --upload --privacy private

# 5. Custom niche for one run
python main.py daily-tip --no-upload --niche "Python coding tips for beginners"
```

**Output:** `output_reels/tips/tip_YYYY-MM-DD.mp4` and `tip_YYYY-MM-DD_*.json`

**GitHub Actions:** `.github/workflows/daily-tip.yml` runs once per day (cron). Use *Actions → Daily Tip Short → Run workflow* to test manually.

If Gemini quota is exceeded, a built-in English fallback tip is used so the pipeline still produces a video.

### Privacy Options

- `private` - Only visible to you (default)
- `unlisted` - Anyone with the link can view
- `public` - Everyone can find and view

## Project Structure

```
AI-Automation/
├── main.py                 # Entry point and CLI
├── config.py               # Configuration and environment variables
├── video_downloader.py     # yt-dlp integration for downloading
├── video_analyzer.py       # Gemini AI analysis
├── video_editor.py         # ffmpeg-based reel creation
├── youtube_uploader.py     # YouTube API upload
├── scheduler.py            # Daily job scheduling
├── tip_generator.py        # Idea 2: Gemini tip scripts
├── tip_video_builder.py    # Idea 2: TTS + faceless video
├── tip_shorts.py           # Idea 2: daily tip pipeline
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (you create this)
├── client_secrets.json     # YouTube OAuth credentials (you create this)
├── downloaded_videos/      # Downloaded source videos
├── output_reels/           # Created reels and analysis files
│   ├── .processed_videos.json  # Deduplication tracking
│   ├── preview/            # Preview reels
│   └── tips/               # Idea 2 daily tip Shorts + JSON
└── youtube_token.pickle    # Saved OAuth token (auto-generated)
```

## GitHub Actions CI/CD

This project includes a GitHub Actions workflow (`.github/workflows/ai.yml`) that can run the automation on a schedule.

### Required Secrets

Set these in your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `YOUTUBE_CLIENT_SECRETS_JSON` | Full content of client_secrets.json |
| `YOUTUBE_TOKEN_PICKLE_B64` | Base64-encoded youtube_token.pickle (get this after first local auth) |

**Getting `YOUTUBE_TOKEN_PICKLE_B64`:**

After authenticating locally, run:
```bash
base64 youtube_token.pickle
```

Copy the output and save it as the secret value.

## Troubleshooting

### "Missing required tools: ffmpeg"
Install ffmpeg as described in the Quick Start section.

### "client_secrets.json not found"
You need to create this file from Google Cloud Console OAuth credentials.

### "Authentication error"
Delete `youtube_token.pickle` and re-run to re-authenticate.

### Reels are being re-created on every run
The system tracks processed videos in `.processed_videos.json`. To re-process, delete this file or the specific entry.

## License

MIT License - See LICENSE file for details.
