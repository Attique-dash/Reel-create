# 🤖 AI YouTube Automation System

Automatically download trending videos, analyze them with AI (Gemini), create YouTube Shorts/Reels, and upload to your channel daily.

## ✨ Features

- **🎬 Video Downloading** - Download videos from YouTube, TikTok, Instagram using yt-dlp
- **🧠 AI Analysis** - Gemini AI extracts hot words, trending topics, and generates metadata
- **✂️ Smart Editing** - Automatically creates vertical Shorts/Reels with captions and hooks
- **📤 Auto Upload** - Uploads to YouTube with SEO-optimized titles, tags, and descriptions
- **⏰ Daily Scheduler** - Runs automatically every day at your specified time
- **📊 Analytics** - Logs all activities for monitoring

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Python 3.8+
python --version

# Install ffmpeg (required for video processing)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html
```

### 2. Setup

```bash
# Clone and enter directory
cd AI-Automation

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env  # or use any text editor
```

### 3. Get API Keys

#### Google Gemini API (FREE)
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy key to `.env` file: `GEMINI_API_KEY=your_key_here`

#### YouTube API (FREE)
1. Go to https://console.cloud.google.com/
2. Create new project
3. Enable "YouTube Data API v3" in APIs & Services > Library
4. Go to Credentials > Create Credentials > OAuth client ID
5. Application type: "Desktop app"
6. Download JSON file, rename to `client_secrets.json`, place in project folder

### 4. First Run

```bash
# Test all components
python main.py test

# Download trending videos
python main.py download --query "viral funny videos"

# Process local videos (analyze, edit, upload)
python main.py run --privacy private

# Start daily automation (runs every day at 9 AM)
python main.py schedule --time 09:00
```

## 📁 Project Structure

```
AI-Automation/
├── main.py                 # Main entry point & CLI
├── config.py               # Configuration settings
├── video_analyzer.py       # AI video analysis with Gemini
├── video_editor.py         # Video editing for Shorts/Reels
├── video_downloader.py     # Video downloading from platforms
├── youtube_uploader.py     # YouTube upload with OAuth2
├── scheduler.py            # Daily automation scheduling
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── AI_AUTOMATION_IDEAS.md  # 30+ additional automation ideas
├── downloaded_videos/      # Source videos folder
├── output_reels/           # Generated Shorts/Reels
└── automation_log.txt      # Execution logs
```

## 🎮 Usage

### Command Line Interface

```bash
# Show help
python main.py help

# Download videos
python main.py download --query "trending tech news" --max 5

# Analyze a specific video
python main.py analyze --video ./downloaded_videos/video.mp4

# Create reels from video
python main.py create --video ./downloaded_videos/video.mp4

# Upload a reel
python main.py upload --video ./output_reels/reel_video.mp4 --privacy public

# Run full pipeline on all videos
python main.py run --privacy private

# Start daily scheduler
python main.py schedule --time 10:30
```

### Privacy Options

- `private` - Only you can see (default, recommended for testing)
- `unlisted` - Anyone with link can view
- `public` - Everyone can see

## ⚙️ How It Works

### 1. Video Acquisition
```
Option A: Download trending videos
- Searches YouTube for trending content
- Downloads top videos

Option B: Use local videos
- Place videos in ./downloaded_videos/
- System will process them
```

### 2. AI Analysis (Gemini)
```
- Extracts audio and transcribes speech
- Analyzes visual content from frames
- Generates:
  • Hot words/trending keywords
  • Viral video titles (3 options)
  • SEO-optimized description
  • Relevant tags/hashtags
  • Best moments for clips
  • Virality score (1-10)
```

### 3. Video Editing
```
- Crops to 9:16 vertical format (1080x1920)
- Extracts best viral segments (15-60 seconds)
- Adds attention-grabbing hook text
- Adds captions/subtitles
- Adds call-to-action at end
- Optimizes for mobile viewing
```

### 4. YouTube Upload
```
- Authenticates with OAuth2
- Uploads with optimized metadata:
  • Title with #Shorts hashtag
  • Description with keywords
  • Tags for discoverability
  • Correct category
- Returns YouTube URL
```

### 5. Daily Automation
```
- Runs at scheduled time every day
- Checks for new content
- Processes and uploads
- Cleans old files
- Logs all activities
```

## 🔧 Configuration

Edit `.env` file:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here
YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json

# Optional
VIDEO_SOURCE_FOLDER=./downloaded_videos
OUTPUT_FOLDER=./output_reels
DAILY_UPLOAD_TIME=09:00
```

Edit `config.py` for advanced settings:

```python
# Video dimensions (9:16 for Shorts/Reels)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Target duration
TARGET_REEL_DURATION_MIN = 15  # seconds
TARGET_REEL_DURATION_MAX = 60  # seconds

# Gemini model (free tier)
GEMINI_MODEL = "gemini-1.5-flash"
```

## 📋 Workflow Examples

### Manual Workflow
```bash
# Step 1: Download videos
python main.py download --query "motivational speeches" --max 3

# Step 2: Run processing pipeline
python main.py run --privacy unlisted

# Step 3: Check logs
cat automation_log.txt
```

### Automated Daily Workflow
```bash
# Start scheduler (runs daily at 9 AM)
python main.py schedule

# Let it run - it will:
# - Download trending videos if none exist
# - Process and create Shorts
# - Upload to YouTube
# - Clean old files
# - Log everything
```

## 🛠️ Troubleshooting

### Common Issues

**"client_secrets.json not found"**
```bash
# Download from Google Cloud Console
# Place in project folder
# See setup step 3
```

**"Gemini API key not set"**
```bash
# Create .env file
echo "GEMINI_API_KEY=your_key" > .env
```

**"ffmpeg not found"**
```bash
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

**"Video upload fails"**
- Check internet connection
- Verify YouTube API quota not exceeded
- Try smaller video file
- Check `automation_log.txt` for details

### Logs

Check `automation_log.txt` for detailed execution logs:

```bash
# View last 50 lines
tail -n 50 automation_log.txt

# Follow logs in real-time
tail -f automation_log.txt
```

## 💡 AI Automation Ideas

See `AI_AUTOMATION_IDEAS.md` for 30+ additional automation projects:

- 📱 Social Media Bots
- 📧 Email Automation
- 💼 Business Tools
- 🎓 Education Assistants
- 🏠 Personal Life Automation
- 🔧 Developer Tools

## 📝 API Limits (Free Tier)

| Service | Free Limit | Notes |
|---------|------------|-------|
| Gemini API | 60 requests/min | Sufficient for daily automation |
| YouTube API | 10,000 units/day | ~100 video uploads/day |
| yt-dlp | Unlimited | Open source |

## 🤝 Contributing

Feel free to extend this project:

1. Add more video sources (Instagram, TikTok)
2. Implement AI voiceover generation
3. Add thumbnail generation with AI
4. Create analytics dashboard
5. Add multi-account support

## ⚠️ Important Notes

1. **Copyright**: Only use videos you have rights to, or use Creative Commons content
2. **YouTube Terms**: Follow YouTube's Terms of Service
3. **Rate Limits**: Respect API limits to avoid bans
4. **Testing**: Always test with `privacy=private` first
5. **Original Content**: Consider creating original content rather than reusing others

## 🆘 Support

If you encounter issues:

1. Check `automation_log.txt`
2. Verify all API keys are correct
3. Ensure `client_secrets.json` is present
4. Test with `python main.py test`
5. Run individual steps to isolate issues

## 📄 License

MIT License - Feel free to use and modify

---

**Happy Automating! 🚀**

Built with ❤️ using Python, Gemini AI, and open-source tools.