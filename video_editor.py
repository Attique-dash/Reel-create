"""
Video Editor Module - Creates YouTube Shorts/Reels using ffmpeg directly
(No MoviePy TextClip dependency to avoid ImageMagick issues in CI)
"""
import os
import json
import random
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from config import (
    OUTPUT_FOLDER, TARGET_REEL_DURATION_MIN, TARGET_REEL_DURATION_MAX,
    VIDEO_WIDTH, VIDEO_HEIGHT
)

PREVIEW_FOLDER = os.path.join(OUTPUT_FOLDER, "preview")


class VideoEditor:
    def __init__(self):
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(PREVIEW_FOLDER, exist_ok=True)
        print(f"[VideoEditor] Output folder   : {OUTPUT_FOLDER}")
        print(f"[VideoEditor] Preview folder  : {PREVIEW_FOLDER}")

    def get_video_info(self, video_path: str) -> Dict:
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries",
                   "format=duration:stream=width,height",
                   "-of", "json", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            info = json.loads(result.stdout)
            duration = float(info["format"]["duration"])
            width = height = 0
            for stream in info.get("streams", []):
                if stream.get("width") and stream.get("height"):
                    width = int(stream["width"])
                    height = int(stream["height"])
                    break
            return {"duration": duration, "width": width, "height": height}
        except Exception as e:
            print(f"[get_video_info] Error: {e}")
            return {"duration": 0, "width": 0, "height": 0}

    def find_segments(self, video_path: str, num_segments: int = 3) -> List[Tuple[float, float]]:
        try:
            info = self.get_video_info(video_path)
            duration = info["duration"]
            if duration == 0:
                return [(0, 15)]
            seg_dur = random.randint(TARGET_REEL_DURATION_MIN, TARGET_REEL_DURATION_MAX)
            segments = []
            for i in range(num_segments):
                center = duration * (i + 1) / (num_segments + 1)
                start = max(0, center - seg_dur / 2)
                end = min(duration, start + seg_dur)
                segments.append((start, end))
            return segments
        except Exception as e:
            print(f"[find_segments] Error: {e}")
            return [(0, 15)]

    def create_reel_ffmpeg(self, video_path: str, start: float, end: float,
                           output_path: str, title: str = "") -> bool:
        """Create a vertical 9:16 reel using pure ffmpeg — no MoviePy needed."""
        try:
            duration = end - start

            # Build video filter: crop to 9:16, scale to 1080x1920
            # Then optionally draw title text on the video
            vf = (
                "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
            )

            # Add text overlay if title is provided (uses ffmpeg drawtext)
            if title:
                # Escape special characters for ffmpeg drawtext
                safe_title = (title[:50]
                              .replace("'", "\\'")
                              .replace(":", "\\:")
                              .replace(",", "\\,"))
                vf += (
                    f",drawtext=text='{safe_title}'"
                    f":fontsize=60:fontcolor=white"
                    f":x=(w-text_w)/2:y=100"
                    f":shadowcolor=black:shadowx=3:shadowy=3"
                    f":box=1:boxcolor=black@0.5:boxborderw=10"
                )

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", video_path,
                "-t", str(duration),
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[ffmpeg] Error: {result.stderr[-300:]}")
                return False

            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"[VideoEditor] Created: {output_path} ({size_mb:.1f} MB)")
                return True
            return False

        except Exception as e:
            print(f"[create_reel_ffmpeg] Error: {e}")
            return False

    def create_preview_reel(self, video_path: str, analysis: Dict,
                            output_name: Optional[str] = None) -> Optional[str]:
        segments = self.find_segments(video_path, num_segments=1)
        if not segments:
            return None
        start, end = segments[0]
        print(f"[create_preview_reel] Segment: {start:.1f}s → {end:.1f}s")

        if output_name is None:
            base_name = Path(video_path).stem[:30]  # limit length
            output_name = f"preview_{base_name}_{int(start)}_{int(end)}.mp4"

        output_path = os.path.join(PREVIEW_FOLDER, output_name)
        title = analysis.get("suggested_titles", ["Check this out!"])[0]

        success = self.create_reel_ffmpeg(video_path, start, end, output_path, title)
        if success:
            print(f"[create_preview_reel] Saved → {output_path}")
            return output_path
        return None

    def create_reel(self, video_path: str, analysis: Dict,
                    output_name: Optional[str] = None) -> Optional[str]:
        segments = self.find_segments(video_path, num_segments=1)
        if not segments:
            return None
        start, end = segments[0]

        if output_name is None:
            base_name = Path(video_path).stem[:30]
            output_name = f"reel_{base_name}_{int(start)}_{int(end)}.mp4"

        output_path = os.path.join(OUTPUT_FOLDER, output_name)
        title = analysis.get("suggested_titles", ["Watch This!"])[0]

        success = self.create_reel_ffmpeg(video_path, start, end, output_path, title)
        return output_path if success else None

    def create_multiple_reels(self, video_path: str, analysis: Dict,
                               max_reels: int = 3) -> List[str]:
        reels = []
        segments = self.find_segments(video_path, num_segments=max_reels)
        base_name = Path(video_path).stem[:30]
        titles = analysis.get("suggested_titles", ["Amazing!", "Watch This!", "Viral Moment!"])

        for i, (start, end) in enumerate(segments):
            output_name = f"reel_{base_name}_part{i + 1}.mp4"
            output_path = os.path.join(OUTPUT_FOLDER, output_name)
            title = titles[min(i, len(titles) - 1)]

            print(f"[create_multiple_reels] Reel {i+1}: {start:.1f}s → {end:.1f}s")
            success = self.create_reel_ffmpeg(video_path, start, end, output_path, title)
            if success:
                reels.append(output_path)

        return reels


if __name__ == "__main__":
    editor = VideoEditor()
    print(f"Output  : {OUTPUT_FOLDER}")
    print(f"Preview : {PREVIEW_FOLDER}")