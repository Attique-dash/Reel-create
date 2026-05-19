# AI YouTube Shorts Automation

Create **original** faceless YouTube Shorts from a text file of topics. Each run picks a **random unused line**, Gemini writes the script, TTS + slides build a 9:16 video, and you can upload to YouTube automatically (twice per day).

## How it works

1. Add topics to `content/video_topics.txt` (one per line)
2. `queue-video` picks a random unused line → AI script → MP4 in `output_reels/queue/`
3. Optional upload to YouTube
4. `schedule-queue` or GitHub Actions runs **2 videos per day** (~12 hours apart)

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) (`brew install ffmpeg` on macOS)
- `GEMINI_API_KEY`
- `client_secrets.json` for YouTube upload

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set GEMINI_API_KEY

python main.py test
python main.py queue-status
python main.py queue-video --no-upload
python main.py queue-video --upload --privacy private
```

First YouTube upload opens a browser once; token saved as `youtube_token.pickle`.

## Commands

| Command | Description |
|---------|-------------|
| `test` | Check setup |
| `queue-status` | Topics used / remaining |
| `queue-video` | Create Short from random line |
| `schedule-queue --upload` | 2 videos/day locally |
| `upload --video path.mp4` | Upload existing file |

```bash
# Fixed topic
python main.py queue-video --topic "What are the top 5 skills to learn in 2026?" --no-upload

# Custom topics file
python main.py queue-video --content-file ./my_topics.txt --upload

# Reset used lines
python main.py queue-status --reset-queue
```

## Environment

| Variable | Default |
|----------|---------|
| `CONTENT_QUEUE_FILE` | `./content/video_topics.txt` |
| `QUEUE_OUTPUT_FOLDER` | `./output_reels/queue` |
| `UPLOAD_TIME_1` / `UPLOAD_TIME_2` | `09:00` / `21:00` |
| `TIP_NICHE` | Context for Gemini |
| `TTS_VOICE` | `en-US-JennyNeural` |

## GitHub Actions

Workflow: `.github/workflows/content-queue.yml` — runs at **09:00 and 21:00 UTC**.

Secrets: `GEMINI_API_KEY`, `YOUTUBE_CLIENT_SECRETS_JSON`, `YOUTUBE_TOKEN_PICKLE_B64`

## Project structure

```
AI-Automation/
├── main.py              # CLI
├── config.py
├── content_queue.py     # Topic file + used-line tracking
├── queue_shorts.py      # Topic → video pipeline
├── tip_generator.py     # Gemini scripts
├── tip_video_builder.py # TTS + slides + ffmpeg
├── youtube_uploader.py
├── scheduler.py
├── content/
│   └── video_topics.txt
└── output_reels/queue/  # Generated MP4 + JSON
```

## License

MIT
