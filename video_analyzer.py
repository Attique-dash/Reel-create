"""
Video Analyzer Module - Analyzes videos and extracts hot words/trending topics using Gemini AI
"""
import os
import json
import base64
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional

from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, VIDEO_SOURCE_FOLDER

# Configure Gemini
client = genai.Client(api_key=GEMINI_API_KEY)


class VideoAnalyzer:
    """Analyzes videos to extract hot words, topics, and generate metadata"""

    def __init__(self):
        self.client = client

    # ------------------------------------------------------------------
    # Audio / frames
    # ------------------------------------------------------------------

    def extract_audio(self, video_path: str, output_audio_path: str) -> bool:
        """Extract audio from video using ffmpeg"""
        try:
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vn", "-acodec", "libmp3lame", "-q:a", "2",
                output_audio_path, "-y",
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return os.path.exists(output_audio_path)
        except Exception as e:
            print(f"[extract_audio] Error: {e}")
            return False

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio to text via Gemini Files API"""
        try:
            # FIX: upload_file is a top-level function in genai, not on the model
            audio_file = genai.upload_file(path=audio_path, mime_type="audio/mpeg")

            # Poll until file is ACTIVE
            for _ in range(10):
                state = genai.get_file(audio_file.name).state.name
                if state == "ACTIVE":
                    break
                if state == "FAILED":
                    print("[transcribe_audio] File processing failed.")
                    return ""
                time.sleep(2)

            prompt = (
                "Please transcribe this audio file. "
                "Return ONLY the transcribed text, no additional commentary."
            )
            response = self.client.models.generate_content(model=GEMINI_MODEL, contents=[prompt, audio_file])
            return response.text.strip() if response.text else ""

        except Exception as e:
            print(f"[transcribe_audio] Error: {e}")
            return ""

    def extract_frames(self, video_path: str, num_frames: int = 5) -> List[str]:
        """Extract evenly-spaced frames from video as JPEG files"""
        frame_paths = []
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())

            interval = duration / (num_frames + 1)
            base_name = Path(video_path).stem

            for i in range(1, num_frames + 1):
                timestamp = i * interval
                frame_path = f"/tmp/frame_{base_name}_{i}.jpg"
                cmd = [
                    "ffmpeg", "-ss", str(timestamp),
                    "-i", video_path,
                    "-vframes", "1", "-q:v", "2",
                    frame_path, "-y",
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                if os.path.exists(frame_path):
                    frame_paths.append(frame_path)

            return frame_paths
        except Exception as e:
            print(f"[extract_frames] Error: {e}")
            return []

    def _frame_to_inline_data(self, frame_path: str) -> Dict:
        """
        FIX: Convert a frame to an inline_data dict for Gemini.
        genai.upload_file() works but requires waiting for processing.
        For frames, inline base64 is faster and simpler.
        """
        with open(frame_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return {"mime_type": "image/jpeg", "data": data}

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    def analyze_video_content(self, video_path: str) -> Dict:
        """Analyze video content using Gemini Vision"""
        try:
            frames = self.extract_frames(video_path, num_frames=5)

            audio_path = f"/tmp/{Path(video_path).stem}.mp3"
            transcript = ""
            if self.extract_audio(video_path, audio_path):
                transcript = self.transcribe_audio(audio_path)
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

            prompt = f"""
Analyze this video content and return ONLY a valid JSON object (no markdown, no backticks).

Fields required:
{{
  "hot_words": ["list", "of", "5-10", "trending", "keywords"],
  "main_topic": "Primary topic/category",
  "key_moments": ["Description of moment 1", "moment 2"],
  "sentiment": "positive | negative | neutral | exciting | funny",
  "target_audience": "Who would enjoy this",
  "virality_score": 7,
  "suggested_titles": ["Title 1", "Title 2", "Title 3"],
  "suggested_description": "Short social media description",
  "tags": ["#tag1", "#tag2"]
}}

Audio transcript (first 1000 chars):
{transcript[:1000] if transcript else "Not available"}
"""

            # FIX: build content list correctly — text prompt + inline image parts
            content_parts = [prompt]
            for frame_path in frames:
                if os.path.exists(frame_path):
                    content_parts.append(
                        {"inline_data": self._frame_to_inline_data(frame_path)}
                    )

            response = self.client.models.generate_content(model=GEMINI_MODEL, contents=content_parts)

            # Clean up frames
            for frame_path in frames:
                try:
                    os.remove(frame_path)
                except OSError:
                    pass

            text = response.text or ""
            # Strip markdown fences if present
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_fallback_analysis(self) -> Dict:
        return {
            "hot_words": ["trending", "viral", "must-watch", "amazing", "insane"],
            "main_topic": "Entertainment",
            "key_moments": ["opening scene", "climax", "ending"],
            "sentiment": "exciting",
            "target_audience": "general audience",
            "virality_score": 7,
            "suggested_titles": [
                "You Won't Believe What Happens Next!",
                "This Changes Everything...",
                "Mind-Blowing Moment Caught on Camera",
            ],
            "suggested_description": (
                "Check out this incredible content! Don't forget to like and subscribe."
            ),
            "tags": ["#viral", "#trending", "#shorts", "#reels", "#entertainment"],
            "transcript": "",
        }

    def get_trending_topics(self, niche: str = "general") -> List[str]:
        """Get current trending topics in a specific niche"""
        try:
            prompt = (
                f"List the top 10 trending topics in the '{niche}' niche right now on "
                "YouTube Shorts, TikTok, and Instagram Reels. "
                "Return ONLY a valid JSON array of strings, no markdown."
            )
            response = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text or ""

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            topics = json.loads(text.strip())
            return topics if isinstance(topics, list) else []

        except Exception as e:
            print(f"[get_trending_topics] Error: {e}")
            return [
                "viral challenges", "life hacks", "funny moments",
                "motivation", "before and after",
            ]

    def generate_video_script(self, topic: str, duration: int = 30) -> Dict:
        """Generate a script for a short video"""
        try:
            prompt = f"""
Create a script for a {duration}-second viral YouTube Short about: {topic}

Return ONLY valid JSON (no markdown):
{{
  "hook": "Attention-grabbing opening line (3-5 seconds)",
  "content": "Main content with timestamps",
  "cta": "Call-to-action for the end",
  "caption_style": "Suggested text overlay style",
  "sound_suggestions": "Trending sound or music style"
}}
"""
            response = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = response.text or ""

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())

        except Exception as e:
            print(f"[generate_video_script] Error: {e}")
            return {
                "hook": f"Wait for it... {topic} will blow your mind!",
                "content": "Engaging content with surprising reveals.",
                "cta": "Follow for more!",
                "caption_style": "Bold, high-contrast text with emojis",
                "sound_suggestions": "Trending upbeat music",
            }


if __name__ == "__main__":
    analyzer = VideoAnalyzer()

    print("Getting trending topics...")
    topics = analyzer.get_trending_topics("technology")
    print(f"Topics: {topics}")

    print("\nGenerating script...")
    script = analyzer.generate_video_script("AI automation", 45)
    print(json.dumps(script, indent=2))