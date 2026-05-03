"""
Video Analyzer Module - Analyzes videos and extracts hot words/trending topics using Gemini AI
"""
import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, VIDEO_SOURCE_FOLDER

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


class VideoAnalyzer:
    """Analyzes videos to extract hot words, topics, and generate metadata"""
    
    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        
    def extract_audio(self, video_path: str, output_audio_path: str) -> bool:
        """Extract audio from video using ffmpeg"""
        try:
            cmd = [
                "ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame",
                "-q:a", "2", output_audio_path, "-y"
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return os.path.exists(output_audio_path)
        except Exception as e:
            print(f"Error extracting audio: {e}")
            return False
    
    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio to text using Gemini (since whisper requires additional setup)"""
        try:
            # Upload audio file to Gemini
            audio_file = genai.upload_file(path=audio_path)
            
            # Ask Gemini to transcribe
            prompt = """
            Please transcribe this audio file. Return ONLY the transcribed text without any additional comments.
            If you cannot understand the audio clearly, provide your best approximation.
            """
            
            response = self.model.generate_content([prompt, audio_file])
            return response.text.strip() if response.text else ""
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return ""
    
    def extract_frames(self, video_path: str, num_frames: int = 5) -> List[str]:
        """Extract frames from video for visual analysis"""
        frame_paths = []
        try:
            # Get video duration
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                   "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())
            
            # Extract frames at regular intervals
            interval = duration / (num_frames + 1)
            base_name = Path(video_path).stem
            
            for i in range(1, num_frames + 1):
                timestamp = i * interval
                frame_path = f"/tmp/frame_{base_name}_{i}.jpg"
                cmd = [
                    "ffmpeg", "-ss", str(timestamp), "-i", video_path,
                    "-vframes", "1", "-q:v", "2", frame_path, "-y"
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                if os.path.exists(frame_path):
                    frame_paths.append(frame_path)
            
            return frame_paths
        except Exception as e:
            print(f"Error extracting frames: {e}")
            return []
    
    def analyze_video_content(self, video_path: str) -> Dict:
        """Analyze video content using Gemini Vision"""
        try:
            # Extract frames
            frames = self.extract_frames(video_path, num_frames=5)
            
            # Extract and transcribe audio
            audio_path = f"/tmp/{Path(video_path).stem}.mp3"
            transcript = ""
            if self.extract_audio(video_path, audio_path):
                transcript = self.transcribe_audio(audio_path)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            
            # Prepare content for analysis
            content_parts = []
            
            prompt = f"""
            Analyze this video content and provide the following information in JSON format:
            
            1. hot_words: List of 5-10 trending/viral keywords related to the content
            2. main_topic: The primary topic/category of the video
            3. key_moments: List of timestamp descriptions for engaging moments (2-5 moments)
            4. sentiment: Overall sentiment (positive, negative, neutral, exciting, funny, etc.)
            5. target_audience: Who would enjoy this content
            6. virality_score: Score from 1-10 on how viral this could be
            7. suggested_titles: 3 catchy YouTube Shorts/Reels titles
            8. suggested_description: Short description for social media
            9. tags: 10-15 relevant hashtags and keywords
            
            Audio Transcript (if available): {transcript[:1000] if transcript else "No transcript available"}
            
            Return ONLY valid JSON without markdown formatting.
            """
            
            content_parts.append(prompt)
            
            # Add frames to analysis
            for frame_path in frames:
                if os.path.exists(frame_path):
                    content_parts.append(genai.upload_file(path=frame_path))
            
            # Generate analysis
            response = self.model.generate_content(content_parts)
            
            # Clean up frames
            for frame_path in frames:
                if os.path.exists(frame_path):
                    os.remove(frame_path)
            
            # Parse JSON response
            text = response.text
            # Extract JSON from markdown if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            analysis = json.loads(text.strip())
            analysis["transcript"] = transcript[:2000]  # Include partial transcript
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing video: {e}")
            return self._get_fallback_analysis()
    
    def _get_fallback_analysis(self) -> Dict:
        """Return fallback analysis if main analysis fails"""
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
                "Mind-Blowing Moment Caught on Camera"
            ],
            "suggested_description": "Check out this incredible content! Don't forget to like and subscribe for more.",
            "tags": ["#viral", "#trending", "#shorts", "#reels", "#entertainment"],
            "transcript": ""
        }
    
    def get_trending_topics(self, niche: str = "general") -> List[str]:
        """Get current trending topics in a specific niche"""
        try:
            prompt = f"""
            What are the top 10 trending topics and hot keywords in the {niche} niche right now?
            These should be topics that are currently viral on YouTube Shorts, TikTok, and Instagram Reels.
            Return as a simple JSON array of strings.
            """
            
            response = self.model.generate_content(prompt)
            text = response.text
            
            # Extract JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            topics = json.loads(text.strip())
            return topics if isinstance(topics, list) else []
            
        except Exception as e:
            print(f"Error getting trending topics: {e}")
            return [
                "viral challenges",
                "life hacks",
                "funny moments",
                "motivation",
                "before and after",
                "satisfying videos",
                "reaction videos"
            ]
    
    def generate_video_script(self, topic: str, duration: int = 30) -> Dict:
        """Generate a script for a short video"""
        try:
            prompt = f"""
            Create a script for a {duration}-second viral YouTube Short/Reel about: {topic}
            
            Provide in this JSON format:
            {{
                "hook": "Attention-grabbing opening line (3-5 seconds)",
                "content": "Main content broken into segments with timestamps",
                "cta": "Call-to-action for the end (2-3 seconds)",
                "caption_style": "Suggested caption/text overlay style",
                "sound_suggestions": "Trending sounds or music style to use"
            }}
            
            Return ONLY valid JSON.
            """
            
            response = self.model.generate_content(prompt)
            text = response.text
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
            
        except Exception as e:
            print(f"Error generating script: {e}")
            return {
                "hook": f"Wait for it... {topic} will blow your mind!",
                "content": "Engaging content about the topic with surprising reveals",
                "cta": "Follow for more! Drop a if you agree!",
                "caption_style": "Bold, high-contrast text with emojis",
                "sound_suggestions": "Trending upbeat music"
            }


if __name__ == "__main__":
    # Test the analyzer
    analyzer = VideoAnalyzer()
    
    # Example: Get trending topics
    print("Getting trending topics...")
    topics = analyzer.get_trending_topics("technology")
    print(f"Trending topics: {topics}")
    
    # Example: Generate script
    print("\nGenerating script...")
    script = analyzer.generate_video_script("AI automation", 45)
    print(f"Script: {json.dumps(script, indent=2)}")
