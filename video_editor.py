"""
Video Editor Module - Creates YouTube Shorts/Reels from source videos
"""
import os
import random
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip,
    concatenate_videoclips, ColorClip
)
from moviepy.video.fx.all import resize, crop, speedx
from config import (
    OUTPUT_FOLDER, TARGET_REEL_DURATION_MIN, TARGET_REEL_DURATION_MAX,
    VIDEO_WIDTH, VIDEO_HEIGHT
)


class VideoEditor:
    """Creates optimized short-form videos for YouTube Shorts/Reels"""
    
    def __init__(self):
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        
    def get_video_info(self, video_path: str) -> Dict:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-show_entries", "stream=width,height", "-of", "json", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = result.stdout
            import json
            info = json.loads(data)
            
            duration = float(info['format']['duration'])
            width = height = 0
            for stream in info.get('streams', []):
                if stream.get('width') and stream.get('height'):
                    width = int(stream['width'])
                    height = int(stream['height'])
                    break
            
            return {
                "duration": duration,
                "width": width,
                "height": height,
                "aspect_ratio": width / height if height > 0 else 0
            }
        except Exception as e:
            print(f"Error getting video info: {e}")
            return {"duration": 0, "width": 0, "height": 0, "aspect_ratio": 0}
    
    def find_viral_segments(self, video_path: str, analysis: Dict, num_segments: int = 3) -> List[Tuple[float, float]]:
        """Find the most engaging segments based on AI analysis"""
        try:
            info = self.get_video_info(video_path)
            duration = info['duration']
            
            segments = []
            segment_duration = random.randint(TARGET_REEL_DURATION_MIN, TARGET_REEL_DURATION_MAX)
            
            # Use key moments from analysis if available
            key_moments = analysis.get("key_moments", [])
            
            if key_moments and duration > 0:
                # Create segments around key moments
                for i in range(min(num_segments, len(key_moments))):
                    # Distribute key moments evenly
                    center = duration * (i + 1) / (len(key_moments) + 1)
                    start = max(0, center - segment_duration / 2)
                    end = min(duration, start + segment_duration)
                    
                    # Adjust if too short
                    if end - start < TARGET_REEL_DURATION_MIN:
                        end = min(duration, start + TARGET_REEL_DURATION_MIN)
                    
                    segments.append((start, end))
            else:
                # Random segments with bias toward middle (usually most engaging)
                for _ in range(num_segments):
                    # Bias toward middle of video
                    center = duration * random.betavariate(2, 2)
                    start = max(0, center - segment_duration / 2)
                    end = min(duration, start + segment_duration)
                    segments.append((start, end))
            
            return segments[:num_segments]
            
        except Exception as e:
            print(f"Error finding segments: {e}")
            return [(0, 30)]  # Default fallback
    
    def crop_to_vertical(self, clip: VideoFileClip, target_width: int = VIDEO_WIDTH, 
                         target_height: int = VIDEO_HEIGHT) -> VideoFileClip:
        """Crop video to 9:16 vertical format for Shorts/Reels"""
        try:
            # Calculate crop dimensions
            target_ratio = target_width / target_height  # 9:16 = 0.5625
            current_ratio = clip.w / clip.h
            
            if current_ratio > target_ratio:
                # Video is wider than 9:16, crop width
                new_width = int(clip.h * target_ratio)
                x_center = clip.w // 2
                x1 = max(0, x_center - new_width // 2)
                cropped = crop(clip, x1=x1, y1=0, width=new_width, height=clip.h)
            else:
                # Video is taller than 9:16, crop height
                new_height = int(clip.w / target_ratio)
                y_center = clip.h // 2
                y1 = max(0, y_center - new_height // 2)
                cropped = crop(clip, x1=0, y1=y1, width=clip.w, height=new_height)
            
            # Resize to target dimensions
            return resize(cropped, width=target_width, height=target_height)
            
        except Exception as e:
            print(f"Error cropping video: {e}")
            return clip
    
    def add_text_overlay(self, clip: VideoFileClip, text: str, position: str = "center",
                         fontsize: int = 60, color: str = "white", 
                         duration: Optional[float] = None) -> CompositeVideoClip:
        """Add styled text overlay to video"""
        try:
            txt_clip = TextClip(
                text, 
                fontsize=fontsize, 
                color=color,
                font="Arial-Bold",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(clip.w - 100, None)
            )
            
            txt_duration = duration or clip.duration
            txt_clip = txt_clip.set_duration(txt_duration)
            
            # Position text
            if position == "center":
                txt_clip = txt_clip.set_position("center")
            elif position == "top":
                txt_clip = txt_clip.set_position(("center", 50))
            elif position == "bottom":
                txt_clip = txt_clip.set_position(("center", clip.h - 200))
            
            return CompositeVideoClip([clip, txt_clip])
            
        except Exception as e:
            print(f"Error adding text: {e}")
            return clip
    
    def add_captions(self, clip: VideoFileClip, transcript: str, 
                     style: str = "bold") -> VideoFileClip:
        """Add animated captions (simplified version)"""
        try:
            # Split transcript into segments
            words = transcript.split()[:20]  # Limit words for short video
            caption_text = " ".join(words)
            
            # Create caption with word highlighting effect
            caption = TextClip(
                caption_text,
                fontsize=50,
                color="white",
                font="Arial-Bold",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(clip.w - 80, None),
                align="center"
            ).set_duration(clip.duration).set_position(("center", clip.h - 250))
            
            return CompositeVideoClip([clip, caption])
            
        except Exception as e:
            print(f"Error adding captions: {e}")
            return clip
    
    def add_background_music(self, video_clip: VideoFileClip, 
                            music_path: Optional[str] = None,
                            volume: float = 0.3) -> VideoFileClip:
        """Add background music to video"""
        try:
            if music_path and os.path.exists(music_path):
                audio = AudioFileClip(music_path).volumex(volume)
                # Loop music if needed
                if audio.duration < video_clip.duration:
                    n_loops = int(video_clip.duration / audio.duration) + 1
                    audio = concatenate_audioclips([audio] * n_loops)
                    audio = audio.subclip(0, video_clip.duration)
                else:
                    audio = audio.subclip(0, video_clip.duration)
                
                # Mix with original audio if present
                if video_clip.audio is not None:
                    final_audio = CompositeAudioClip([video_clip.audio, audio])
                else:
                    final_audio = audio
                
                return video_clip.set_audio(final_audio)
            
            return video_clip
            
        except Exception as e:
            print(f"Error adding music: {e}")
            return video_clip
    
    def enhance_video(self, clip: VideoFileClip, speed_factor: float = 1.0) -> VideoFileClip:
        """Apply video enhancements"""
        try:
            # Adjust speed if needed
            if speed_factor != 1.0:
                clip = speedx(clip, factor=speed_factor)
            
            # Ensure consistent frame rate
            clip = clip.set_fps(30)
            
            return clip
            
        except Exception as e:
            print(f"Error enhancing video: {e}")
            return clip
    
    def create_reel(self, video_path: str, analysis: Dict, 
                    output_name: Optional[str] = None) -> Optional[str]:
        """Create a YouTube Short/Reel from a source video"""
        try:
            # Find viral segments
            segments = self.find_viral_segments(video_path, analysis)
            
            if not segments:
                print("No segments found")
                return None
            
            # Choose the best segment (use first one)
            start, end = segments[0]
            
            # Load video segment
            clip = VideoFileClip(video_path).subclip(start, end)
            
            # Crop to vertical format
            clip = self.crop_to_vertical(clip)
            
            # Add hook text
            hook_text = analysis.get("suggested_titles", ["Wait for it..."])[0]
            hook_duration = min(3, clip.duration * 0.2)
            hook_clip = self.add_text_overlay(
                clip.subclip(0, hook_duration),
                hook_text,
                position="center",
                fontsize=70
            )
            
            # Rest of the clip
            rest_clip = clip.subclip(hook_duration)
            
            # Add captions if transcript available
            transcript = analysis.get("transcript", "")
            if transcript:
                rest_clip = self.add_captions(rest_clip, transcript)
            
            # Combine hook and rest
            final_clip = concatenate_videoclips([hook_clip, rest_clip])
            
            # Add call-to-action at the end
            cta_duration = min(2, final_clip.duration * 0.1)
            main_part = final_clip.subclip(0, final_clip.duration - cta_duration)
            cta_part = self.add_text_overlay(
                final_clip.subclip(final_clip.duration - cta_duration, final_clip.duration),
                "Follow for more!",
                position="center",
                fontsize=60
            )
            final_clip = concatenate_videoclips([main_part, cta_part])
            
            # Enhance video
            final_clip = self.enhance_video(final_clip)
            
            # Generate output filename
            if output_name is None:
                base_name = Path(video_path).stem
                output_name = f"reel_{base_name}_{int(start)}_{int(end)}.mp4"
            
            output_path = os.path.join(OUTPUT_FOLDER, output_name)
            
            # Export video
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=f"/tmp/tmp_audio_{output_name}",
                remove_temp=True,
                threads=4,
                preset="medium"
            )
            
            # Clean up
            clip.close()
            final_clip.close()
            
            print(f"Reel created: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error creating reel: {e}")
            return None
    
    def create_multiple_reels(self, video_path: str, analysis: Dict, 
                              max_reels: int = 3) -> List[str]:
        """Create multiple reels from one source video"""
        reels = []
        segments = self.find_viral_segments(video_path, analysis, num_segments=max_reels)
        
        base_name = Path(video_path).stem
        
        for i, (start, end) in enumerate(segments):
            try:
                output_name = f"reel_{base_name}_part{i+1}.mp4"
                
                # Load specific segment
                clip = VideoFileClip(video_path).subclip(start, end)
                clip = self.crop_to_vertical(clip)
                
                # Add variations for each reel
                title = analysis.get("suggested_titles", [f"Amazing Content Part {i+1}"])[min(i, 2)]
                
                # Add title overlay
                clip = self.add_text_overlay(clip, title, position="center", fontsize=65)
                
                # Add captions
                transcript = analysis.get("transcript", "")
                if transcript:
                    words = transcript.split()
                    segment_text = " ".join(words[i*5:(i+1)*5 + 10])
                    clip = self.add_captions(clip, segment_text)
                
                # Export
                output_path = os.path.join(OUTPUT_FOLDER, output_name)
                clip.write_videofile(
                    output_path,
                    fps=30,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=f"/tmp/tmp_audio_{i}",
                    remove_temp=True,
                    threads=4,
                    preset="medium"
                )
                
                reels.append(output_path)
                clip.close()
                
            except Exception as e:
                print(f"Error creating reel {i+1}: {e}")
                continue
        
        return reels


if __name__ == "__main__":
    # Test the editor
    editor = VideoEditor()
    print("VideoEditor initialized successfully")
    print(f"Output folder: {OUTPUT_FOLDER}")
