# Video Processor - AI-Powered Short Content Creator

Transform long videos into engaging short clips (TikTok, Instagram Reels, YouTube Shorts) using AI analysis.

## Features

- **Video Upload & URL Processing**: Upload video files or paste URLs from YouTube, Vimeo, Instagram, or TikTok
- **AI-Powered Analysis**: Automatic transcription using Whisper and moment detection using Gemini Flash
- **Smart Video Processing**: Automatic clip generation, subtitle burning, and smart cropping with face detection
- **User Controls**: Adjustable number of clips, duration, aspect ratio, and subtitle customization
- **In-Browser Editor**: Timeline-based clip editing with real-time preview
- **Export & Sharing**: Download clips or post directly to social platforms

## Tech Stack

### Frontend
- Next.js 14+ (React 18+)
- TailwindCSS
- Remotion (video editor)
- Zustand (state management)

### Backend
- FastAPI (Python)
- Celery + Redis (background processing)
- MongoDB (database)

### Video Processing
- yt-dlp (video download)
- OpenAI Whisper (transcription)
- Google Gemini Flash (AI analysis)
- FFmpeg (video editing)
- OpenCV/MediaPipe (smart cropping)

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for local development)
- FFmpeg (for video processing)

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd AI-Automation
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

4. Start all services:
```bash
docker-compose up -d
```

5. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
export GEMINI_API_KEY=your_gemini_api_key_here
export MONGODB_URI=mongodb://localhost:27017
export REDIS_URL=redis://localhost:6379/0
```

5. Start MongoDB and Redis (using Docker):
```bash
docker-compose up -d mongodb redis
```

6. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

7. Start Celery worker (in another terminal):
```bash
celery -A app.workers.celery_worker worker --loglevel=info
```

#### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Set environment variable:
```bash
export NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Start the development server:
```bash
npm run dev
```

5. Access the application at http://localhost:3000

## Project Structure

```
AI-Automation/
├── frontend/                 # Next.js application
│   ├── app/                 # App router pages
│   ├── components/          # React components
│   └── lib/                 # Utilities and API client
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── services/       # Video processing services
│   │   ├── models/         # Pydantic models
│   │   ├── workers/        # Celery workers
│   │   └── database/       # MongoDB connection
│   └── requirements.txt
├── storage/                  # File storage
│   ├── uploads/            # Uploaded videos
│   ├── processed/          # Processed clips
│   └── subtitles/          # SRT/VTT files
└── docker-compose.yml       # Docker orchestration
```

## API Endpoints

### Upload
- `POST /api/upload` - Upload video file
- `POST /api/upload/url` - Submit video URL

### Process
- `GET /api/process/jobs/{job_id}` - Get job status
- `GET /api/process/jobs` - List all jobs

### Download
- `GET /api/download/{clip_id}` - Download specific clip
- `GET /api/download/job/{job_id}` - Download all clips as zip

## Environment Variables

See `.env.example` for all available environment variables.

## Development Phases

- [x] Phase 1: Core Infrastructure
- [x] Phase 2: Video Processing
- [x] Phase 3: AI Integration
- [x] Phase 4: Smart Cropping
- [ ] Phase 5: User Interface
- [ ] Phase 6: Export & Social Integration

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
