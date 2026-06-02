# Video Processing Pipeline - Project Plan

## Overview
A self-hosted video processing platform that automatically creates short-form content (TikTok, Reels, YouTube Shorts) from long-form videos using AI analysis.

## Architecture Flow

```
User Input → Processing Core → Video Processing → User Controls → Final Output
```

### 1. User Input
- **Upload video file** (MP4, MOV, AVI, etc.)
- **Paste URL** (YouTube, Vimeo, Instagram, TikTok)

### 2. Processing Core
- **AI Analysis Engine**: Whisper (transcription) + Gemini Flash (moment detection)
- Analyzes video content to find most engaging moments
- Ranks segments based on engagement potential

### 3. Video Processing
- **Clip Cutter**: FFmpeg - trims clips at exact timestamps
- **Subtitle Burner**: FFmpeg + Whisper SRT - burns subtitles onto video
- **Auto Crop**: OpenCV/MediaPipe - smart 9:16 vertical framing with face detection

### 4. User Controls + Output
- **Output Settings Panel**: 
  - Number of clips
  - Duration per clip
  - Aspect ratio (9:16, 1:1, 16:9)
  - Subtitle style (font, color, position)
  - Auto-tags generation

### 5. Optional Edit
- **In-Browser Editor** (Remotion/Fabric.js):
  - Trim clips
  - Resize text
  - Change tags
  - Preview before download

### 6. Final Output
- **Download MP4**: All clips zipped
- **Post to Social**: TikTok, Instagram Reels, YouTube Shorts
- **Export SRT/VTT**: Subtitle files
- **Tags + SEO**: AI-generated metadata

## Tech Stack

### Frontend
- **Framework**: Next.js 14+ (React 18+)
- **UI Components**: shadcn/ui
- **Video Editor**: Remotion (for timeline-based editing) or Fabric.js
- **Styling**: TailwindCSS
- **State Management**: React Context + Zustand
- **API Client**: Axios / Fetch

### Backend
- **Framework**: FastAPI (Python)
- **Task Queue**: Celery + Redis (background processing)
- **Database**: MongoDB (user jobs, clip metadata, tags, history)
- **File Storage**: Local filesystem (with S3-compatible option)

### Video Processing
- **Video Download**: yt-dlp (YouTube, Vimeo, Instagram, TikTok)
- **Transcription**: OpenAI Whisper (local)
- **AI Analysis**: Google Gemini Flash (GEMINI_API_KEY)
- **Video Editing**: FFmpeg
- **Smart Cropping**: OpenCV or MediaPipe (face detection)
- **Subtitle Generation**: Whisper (SRT/VTT output)

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Environment**: .env file for API keys and configuration
- **Monitoring**: Celery flower for task monitoring

## Project Structure

```
AI-Automation/
├── frontend/                 # Next.js application
│   ├── app/
│   │   ├── page.tsx         # Landing page
│   │   ├── upload/          # Video upload page
│   │   ├── editor/          # In-browser editor
│   │   └── dashboard/       # User dashboard
│   ├── components/
│   │   ├── ui/              # shadcn/ui components
│   │   ├── VideoUploader.tsx
│   │   ├── SettingsPanel.tsx
│   │   ├── ClipEditor.tsx
│   │   └── OutputPreview.tsx
│   ├── lib/
│   │   └── api.ts           # API client
│   └── package.json
│
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── api/
│   │   │   ├── upload.py    # Upload endpoints
│   │   │   ├── process.py   # Processing endpoints
│   │   │   └── download.py  # Download endpoints
│   │   ├── services/
│   │   │   ├── video_downloader.py  # yt-dlp wrapper
│   │   │   ├── transcriber.py       # Whisper wrapper
│   │   │   ├── ai_analyzer.py       # Gemini Flash
│   │   │   ├── video_editor.py      # FFmpeg wrapper
│   │   │   └── smart_crop.py        # OpenCV/MediaPipe
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic models
│   │   ├── workers/
│   │   │   └── celery_worker.py  # Background tasks
│   │   └── database/
│   │       └── mongodb.py    # MongoDB connection
│   ├── requirements.txt
│   └── Dockerfile
│
├── shared/                   # Shared types and utilities
│   └── types.ts
│
├── storage/                  # File storage
│   ├── uploads/             # Uploaded videos
│   ├── processed/           # Processed clips
│   └── subtitles/           # SRT/VTT files
│
├── docker-compose.yml        # Orchestration
├── .env.example             # Environment variables template
├── .env                     # Actual environment variables (gitignored)
└── README.md                # Project documentation
```

## Environment Variables

```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here

# Database
MONGODB_URI=mongodb://localhost:27017/video_processor
REDIS_URL=redis://localhost:6379/0

# Storage
UPLOAD_DIR=./storage/uploads
PROCESSED_DIR=./storage/processed
SUBTITLE_DIR=./storage/subtitles

# Processing
MAX_CLIP_DURATION=60
DEFAULT_ASPECT_RATIO=9:16
DEFAULT_SUBTITLE_FONT=Arial
DEFAULT_SUBTITLE_SIZE=24

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key Features

### 1. Video Upload & URL Processing
- Drag-and-drop video upload
- URL paste with validation
- Progress tracking for large files
- Support for multiple video formats

### 2. AI-Powered Analysis
- Automatic transcription using Whisper
- Sentiment analysis and engagement scoring
- Moment detection using Gemini Flash
- Auto-tagging with SEO keywords

### 3. Smart Video Processing
- Automatic clip generation based on AI analysis
- Subtitle burning with customizable styles
- Smart cropping with face detection
- Resolution optimization for social platforms

### 4. User Controls
- Adjustable number of clips
- Custom duration per clip
- Aspect ratio selection (9:16, 1:1, 16:9)
- Subtitle customization (font, color, position)

### 5. In-Browser Editor
- Timeline-based clip editing
- Text overlay customization
- Real-time preview
- Export options

### 6. Export & Sharing
- Download as MP4 (individual or zipped)
- Direct posting to social platforms
- Export subtitles (SRT/VTT)
- Export metadata and tags

## Development Phases

### Phase 1: Core Infrastructure
- Set up Next.js frontend
- Set up FastAPI backend
- Configure MongoDB and Redis
- Set up Celery for background tasks

### Phase 2: Video Processing
- Implement yt-dlp for video download
- Implement Whisper for transcription
- Implement FFmpeg for video cutting
- Implement subtitle burning

### Phase 3: AI Integration
- Integrate Gemini Flash for moment detection
- Implement engagement scoring
- Add auto-tagging functionality

### Phase 4: Smart Cropping
- Implement OpenCV/MediaPipe for face detection
- Add smart framing logic
- Optimize for vertical formats

### Phase 5: User Interface
- Build upload interface
- Build settings panel
- Build in-browser editor
- Build dashboard

### Phase 6: Export & Social Integration
- Implement download functionality
- Add social platform APIs
- Add batch export options

## Deployment Options

### Self-Hosted (Recommended)
- Docker Compose for local development
- VPS deployment (DigitalOcean, AWS, GCP)
- Full control over data and processing

### Cloud (Paid APIs)
- Use cloud-based Whisper API
- Use cloud-based Gemini API
- S3 for file storage
- Managed Redis and MongoDB

## Security Considerations
- API key encryption
- File upload size limits
- Rate limiting
- User authentication (future)
- Data encryption at rest

## Performance Optimization
- Async processing with Celery
- Video compression before processing
- Caching of transcriptions
- Parallel processing for multiple clips
- CDN for static assets
