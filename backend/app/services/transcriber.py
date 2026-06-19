import whisper
import os
import logging
from datetime import timedelta

SUBTITLE_DIR = os.getenv("SUBTITLE_DIR", "./storage/subtitles")
logger = logging.getLogger(__name__)

def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(int(td.total_seconds()), 3600)
    minutes, seconds_int = divmod(remainder, 60)
    milliseconds = int((td.total_seconds() % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds_int:02d},{milliseconds:03d}"

def transcribe_video(video_path: str) -> dict:
    """Transcribe video using Whisper with proper error handling"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    try:
        logger.info(f"Starting transcription for: {video_path}")
        model = whisper.load_model("base")
        result = model.transcribe(video_path, language="en")
        
        # Save subtitles with proper SRT format
        os.makedirs(SUBTITLE_DIR, exist_ok=True)
        subtitle_path = os.path.join(SUBTITLE_DIR, f"{os.path.basename(video_path)}.srt")
        
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            for idx, segment in enumerate(result['segments'], 1):
                start = _format_timestamp(segment['start'])
                end = _format_timestamp(segment['end'])
                text = segment['text'].strip()
                f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")
        
        logger.info(f"Transcription completed. Segments: {len(result['segments'])}")
        
        # Calculate video duration from segments
        duration = result['segments'][-1]['end'] if result['segments'] else 0
        
        return {
            "text": result['text'],
            "segments": result['segments'],
            "subtitle_path": subtitle_path,
            "duration": duration,
            "language": result.get('language', 'en')
        }
    except Exception as e:
        logger.error(f"Transcription failed for {video_path}: {str(e)}")
        raise
