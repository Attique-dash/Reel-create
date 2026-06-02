import whisper
import os

SUBTITLE_DIR = os.getenv("SUBTITLE_DIR", "./storage/subtitles")

def transcribe_video(video_path: str) -> dict:
    """Transcribe video using Whisper"""
    model = whisper.load_model("base")
    result = model.transcribe(video_path)
    
    # Save subtitles
    os.makedirs(SUBTITLE_DIR, exist_ok=True)
    subtitle_path = os.path.join(SUBTITLE_DIR, f"{os.path.basename(video_path)}.srt")
    
    with open(subtitle_path, 'w', encoding='utf-8') as f:
        for segment in result['segments']:
            start = segment['start']
            end = segment['end']
            text = segment['text']
            f.write(f"{start} --> {end}\n{text}\n\n")
    
    return {
        "text": result['text'],
        "segments": result['segments'],
        "subtitle_path": subtitle_path
    }
