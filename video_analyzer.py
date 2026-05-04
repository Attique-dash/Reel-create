"""
Video Analyzer Module - Analyzes videos using Gemini AI
"""
import os
import json
import base64
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional

from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)


class VideoAnalyzer:
    def __init__(self):
        self.client = client

    def extract_audio(self, video_path: str, output_audio_path: str) -> bool:
        try:
            cmd = ["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame",
                   "-q:a", "2", output_audio_path, "-y"]
            subprocess.run(cmd, capture_output=True, check=True)
            return os.path.exists(output_audio_path)
        except Exception as e:
            print(f"[extract_audio] Error: {e}")
            return False

    def transcribe_audio(self, audio_path: str) -> str:
        try:
            audio_file = self.client.files.upload(
                path=audio_path,
                config={"mime_type": "audio/mpeg"}
            )
            for _ in range(10):
                file_info = self.client.files.get(name=audio_file.name)
                if file_info.state.name == "ACTIVE":
                    break
                if file_info.state.name == "FAILED":
                    return ""
                time.sleep(2)
            prompt = "Transcribe this audio. Return ONLY the transcribed text."
            response = self.client.models.generate_content(
                model=GEMINI_MODEL, contents=[prompt, audio_file])
            return response.text.strip() if response.text else ""
        except Exception as e:
            print(f"[transcribe_audio] Error: {e}")
            return ""

    def extract_frames(self, video_path: str, num_frames: int = 5) -> List[str]:
        frame_paths = []
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout.strip()
            if not output:
                return []
            duration = float(output)
            interval = duration / (num_frames + 1)
            base_name = Path(video_path).stem
            for i in range(1, num_frames + 1):
                timestamp = i * interval
                frame_path = f"/tmp/frame_{base_name}_{i}.jpg"
                cmd2 = ["ffmpeg", "-ss", str(timestamp), "-i", video_path,
                        "-vframes", "1", "-q:v", "2", frame_path, "-y"]
                subprocess.run(cmd2, capture_output=True, check=True)
                if os.path.exists(frame_path):
                    frame_paths.append(frame_path)
            return frame_paths
        except Exception as e:
            print(f"[extract_frames] Error: {e}")
            return []

    def _frame_to_inline_data(self, frame_path: str) -> Dict:
        with open(frame_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return {"mime_type": "image/jpeg", "data": data}

    def analyze_video_content(self, video_path: str) -> Dict:
        try:
            frames = self.extract_frames(video_path, num_frames=3)
            audio_path = f"/tmp/{Path(video_path).stem}.mp3"
            transcript = ""
            if self.extract_audio(video_path, audio_path):
                transcript = self.transcribe_audio(audio_path)
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

            prompt = f"""Analyze this video and return ONLY valid JSON, no markdown, no backticks:
{{
  "hot_words": ["keyword1", "keyword2", "keyword3"],
  "main_topic": "Entertainment",
  "key_moments": ["moment1", "moment2"],
  "sentiment": "exciting",
  "target_audience": "general audience",
  "virality_score": 7,
  "suggested_titles": ["Title 1", "Title 2", "Title 3"],
  "suggested_description": "Short description here",
  "tags": ["#tag1", "#tag2"]
}}
Audio transcript: {transcript[:500] if transcript else "Not available"}"""

            content_parts = [prompt]
            for frame_path in frames:
                if os.path.exists(frame_path):
                    content_parts.append({"inline_data": self._frame_to_inline_data(frame_path)})

            response = self.client.models.generate_content(
                model=GEMINI_MODEL, contents=content_parts)

            for frame_path in frames:
                try:
                    os.remove(frame_path)
                except OSError:
                    pass

            text = response.text or ""
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            analysis = json.loads(text.strip())
            analysis["transcript"] = transcript[:2000]
            return analysis

        except Exception as e:
            print(f"[analyze_video_content] Error: {e}")
            return self._get_fallback_analysis()

    def _get_fallback_analysis(self) -> Dict:
        return {
            "hot_words": ["trending", "viral", "amazing"],
            "main_topic": "Entertainment",
            "key_moments": ["opening", "climax", "ending"],
            "sentiment": "exciting",
            "target_audience": "general audience",
            "virality_score": 7,
            "suggested_titles": [
                "You Won't Believe This!",
                "This Changes Everything...",
                "Mind-Blowing Moment!",
            ],
            "suggested_description": "Check out this incredible content!",
            "tags": ["#viral", "#trending", "#shorts"],
            "transcript": "",
        }

    def get_trending_topics(self, niche: str = "general") -> List[str]:
        try:
            prompt = (f"List 5 trending topics in '{niche}' for YouTube Shorts. "
                      "Return ONLY a JSON array of strings, no markdown.")
            response = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text or ""
            if "```" in text:
                text = text.split("```")[1].split("```")[0]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            print(f"[get_trending_topics] Error: {e}")
            return ["viral challenges", "life hacks", "funny moments", "motivation"]