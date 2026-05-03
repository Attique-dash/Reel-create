"""
Video Editor Module - Creates YouTube Shorts/Reels from source videos
"""
import os
import json
import random
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip,
    concatenate_videoclips, ColorClip, CompositeAudioClip  # FIX: added CompositeAudioClip
)
# FIX: Do NOT import resize/crop/speedx from fx.all as standalone functions.
# Use clip.resize(), clip.crop(), clip.fx(speedx) instead.
from moviepy.video.fx.all import speedx

from config import (
    OUTPUT_FOLDER, TARGET_REEL_DURATION_MIN, TARGET_REEL_DURATION_MAX,
    VIDEO_WIDTH, VIDEO_HEIGHT
)

# FIX: Separate preview folder so reels are saved for review BEFORE upload
PREVIEW_FOLDER = os.path.join(OUTPUT_FOLDER, "preview")


class VideoEditor:
    """Creates optimized short-form videos for YouTube Shorts/Reels"""

    def __init__(self):
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(PREVIEW_FOLDER, exist_ok=True)  # FIX: create preview folder
        print(f"[VideoEditor] Output folder   : {OUTPUT_FOLDER}")
        print(f"[VideoEditor] Preview folder  : {PREVIEW_FOLDER}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_video_info(self, video_path: str) -> Dict:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-show_entries", "stream=width,height",
                "-of", "json", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            info = json.loads(result.stdout)

            duration = float(info["format"]["duration"])
            width = height = 0
            for stream in info.get("streams", []):
                if stream.get("width") and stream.get("height"):
                    width = int(stream["width"])
                    height = int(stream["height"])
                    break

            return {
                "duration": duration,
                "width": width,
                "height": height,
                "aspect_ratio": width / height if height > 0 else 0,
            }
        except Exception as e:
            print(f"[get_video_info] Error: {e}")
            return {"duration": 0, "width": 0, "height": 0, "aspect_ratio": 0}

    def find_viral_segments(
        self, video_path: str, analysis: Dict, num_segments: int = 3
    ) -> List[Tuple[float, float]]:
        """Find the most engaging segments based on AI analysis"""
        try:
            info = self.get_video_info(video_path)
            duration = info["duration"]
            if duration == 0:
                return [(0, min(15, 15))]

            # FIX: use the shorter 10-15 s window as requested
            segment_duration = random.randint(
                TARGET_REEL_DURATION_MIN, TARGET_REEL_DURATION_MAX
            )

            key_moments = analysis.get("key_moments", [])
            segments = []

            if key_moments:
                for i in range(min(num_segments, len(key_moments))):
                    center = duration * (i + 1) / (len(key_moments) + 1)
                    start = max(0, center - segment_duration / 2)
                    end = min(duration, start + segment_duration)
                    if end - start < TARGET_REEL_DURATION_MIN:
                        end = min(duration, start + TARGET_REEL_DURATION_MIN)
                    segments.append((start, end))
            else:
                for _ in range(num_segments):
                    center = duration * random.betavariate(2, 2)
                    start = max(0, center - segment_duration / 2)
                    end = min(duration, start + segment_duration)
                    segments.append((start, end))

            return segments[:num_segments]

        except Exception as e:
            print(f"[find_viral_segments] Error: {e}")
            return [(0, 15)]

    # ------------------------------------------------------------------
    # Core editing
    # ------------------------------------------------------------------

    def crop_to_vertical(
        self,
        clip: VideoFileClip,
        target_width: int = VIDEO_WIDTH,
        target_height: int = VIDEO_HEIGHT,
    ) -> VideoFileClip:
        """Crop video to 9:16 vertical format for Shorts/Reels"""
        try:
            target_ratio = target_width / target_height  # ≈ 0.5625
            current_ratio = clip.w / clip.h

            if current_ratio > target_ratio:
                # Wider than 9:16 — crop the sides
                new_width = int(clip.h * target_ratio)
                x1 = (clip.w - new_width) // 2
                # FIX: use clip.crop() not the standalone crop()
                cropped = clip.crop(x1=x1, y1=0, x2=x1 + new_width, y2=clip.h)
            else:
                # Taller than 9:16 — crop top/bottom
                new_height = int(clip.w / target_ratio)
                y1 = (clip.h - new_height) // 2
                cropped = clip.crop(x1=0, y1=y1, x2=clip.w, y2=y1 + new_height)

            # FIX: use clip.resize() not the standalone resize()
            return cropped.resize((target_width, target_height))

        except Exception as e:
            print(f"[crop_to_vertical] Error: {e}")
            return clip

    def add_text_overlay(
        self,
        clip: VideoFileClip,
        text: str,
        position: str = "center",
        fontsize: int = 60,
        color: str = "white",
        duration: Optional[float] = None,
    ) -> CompositeVideoClip:
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
                size=(clip.w - 100, None),
            )

            txt_duration = duration or clip.duration
            txt_clip = txt_clip.set_duration(txt_duration)

            if position == "center":
                txt_clip = txt_clip.set_position("center")
            elif position == "top":
                txt_clip = txt_clip.set_position(("center", 50))
            elif position == "bottom":
                txt_clip = txt_clip.set_position(("center", clip.h - 200))

            return CompositeVideoClip([clip, txt_clip])

        except Exception as e:
            print(f"[add_text_overlay] Error: {e}")
            return clip

    def add_captions(
        self, clip: VideoFileClip, transcript: str, style: str = "bold"
    ) -> VideoFileClip:
        """Add captions at the bottom of the clip"""
        try:
            words = transcript.split()[:20]
            caption_text = " ".join(words)

            caption = (
                TextClip(
                    caption_text,
                    fontsize=50,
                    color="white",
                    font="Arial-Bold",
                    stroke_color="black",
                    stroke_width=3,
                    method="caption",
                    size=(clip.w - 80, None),
                    align="center",
                )
                .set_duration(clip.duration)
                .set_position(("center", clip.h - 250))
            )

            return CompositeVideoClip([clip, caption])

        except Exception as e:
            print(f"[add_captions] Error: {e}")
            return clip

    def add_background_music(
        self,
        video_clip: VideoFileClip,
        music_path: Optional[str] = None,
        volume: float = 0.3,
    ) -> VideoFileClip:
        """Add background music to video"""
        try:
            if music_path and os.path.exists(music_path):
                audio = AudioFileClip(music_path).volumex(volume)

                if audio.duration < video_clip.duration:
                    from moviepy.editor import concatenate_audioclips  # FIX: proper import
                    n_loops = int(video_clip.duration / audio.duration) + 1
                    audio = concatenate_audioclips([audio] * n_loops)

                audio = audio.subclip(0, video_clip.duration)

                if video_clip.audio is not None:
                    # FIX: CompositeAudioClip is now properly imported at top
                    final_audio = CompositeAudioClip([video_clip.audio, audio])
                else:
                    final_audio = audio

                return video_clip.set_audio(final_audio)

            return video_clip

        except Exception as e:
            print(f"[add_background_music] Error: {e}")
            return video_clip

    def enhance_video(
        self, clip: VideoFileClip, speed_factor: float = 1.0
    ) -> VideoFileClip:
        """Apply video enhancements"""
        try:
            if speed_factor != 1.0:
                # FIX: use clip.fx(speedx, ...) not speedx(clip, ...)
                clip = clip.fx(speedx, factor=speed_factor)
            clip = clip.set_fps(30)
            return clip
        except Exception as e:
            print(f"[enhance_video] Error: {e}")
            return clip

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def _export(self, clip: VideoFileClip, output_path: str, temp_tag: str = "tmp"):
        """Write video file with consistent settings"""
        clip.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=f"/tmp/tmp_audio_{temp_tag}.aac",
            remove_temp=True,
            threads=4,
            preset="medium",
            logger=None,  # suppress verbose moviepy logs
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_preview_reel(
        self,
        video_path: str,
        analysis: Dict,
        output_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create ONE reel and save it to the PREVIEW folder.
        Review the preview before uploading — it will NOT be uploaded automatically.
        """
        try:
            segments = self.find_viral_segments(video_path, analysis, num_segments=1)
            if not segments:
                print("[create_preview_reel] No segments found.")
                return None

            start, end = segments[0]
            print(f"[create_preview_reel] Segment: {start:.1f}s → {end:.1f}s")

            clip = VideoFileClip(video_path).subclip(start, end)
            clip = self.crop_to_vertical(clip)

            # Hook text
            hook_text = analysis.get("suggested_titles", ["Check this out!"])[0]
            hook_duration = min(3.0, clip.duration * 0.2)

            hook_part = self.add_text_overlay(
                clip.subclip(0, hook_duration),
                hook_text,
                position="center",
                fontsize=65,
            )
            rest_part = clip.subclip(hook_duration)

            transcript = analysis.get("transcript", "")
            if transcript:
                rest_part = self.add_captions(rest_part, transcript)

            final_clip = concatenate_videoclips([hook_part, rest_part])
            final_clip = self.enhance_video(final_clip)

            if output_name is None:
                base_name = Path(video_path).stem
                output_name = f"preview_{base_name}_{int(start)}_{int(end)}.mp4"

            # FIX: save to PREVIEW folder, not OUTPUT folder
            output_path = os.path.join(PREVIEW_FOLDER, output_name)
            self._export(final_clip, output_path, temp_tag=output_name)

            clip.close()
            final_clip.close()

            print(f"[create_preview_reel] Saved preview → {output_path}")
            print("  ▶  Watch this file BEFORE uploading to YouTube.")
            return output_path

        except Exception as e:
            print(f"[create_preview_reel] Error: {e}")
            return None

    def create_reel(
        self,
        video_path: str,
        analysis: Dict,
        output_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a reel and save it to the main OUTPUT folder (ready for upload).
        Call create_preview_reel() first to verify quality.
        """
        try:
            segments = self.find_viral_segments(video_path, analysis, num_segments=1)
            if not segments:
                return None

            start, end = segments[0]
            clip = VideoFileClip(video_path).subclip(start, end)
            clip = self.crop_to_vertical(clip)

            hook_text = analysis.get("suggested_titles", ["Check this out!"])[0]
            hook_duration = min(3.0, clip.duration * 0.2)

            hook_part = self.add_text_overlay(
                clip.subclip(0, hook_duration), hook_text, position="center", fontsize=65
            )
            rest_part = clip.subclip(hook_duration)

            transcript = analysis.get("transcript", "")
            if transcript:
                rest_part = self.add_captions(rest_part, transcript)

            final_clip = concatenate_videoclips([hook_part, rest_part])
            final_clip = self.enhance_video(final_clip)

            if output_name is None:
                base_name = Path(video_path).stem
                output_name = f"reel_{base_name}_{int(start)}_{int(end)}.mp4"

            output_path = os.path.join(OUTPUT_FOLDER, output_name)
            self._export(final_clip, output_path, temp_tag=output_name)

            clip.close()
            final_clip.close()

            print(f"[create_reel] Reel ready → {output_path}")
            return output_path

        except Exception as e:
            print(f"[create_reel] Error: {e}")
            return None

    def create_multiple_reels(
        self, video_path: str, analysis: Dict, max_reels: int = 3
    ) -> List[str]:
        """Create multiple reels (saved to OUTPUT folder, ready for upload)"""
        reels = []
        segments = self.find_viral_segments(video_path, analysis, num_segments=max_reels)
        base_name = Path(video_path).stem

        for i, (start, end) in enumerate(segments):
            try:
                output_name = f"reel_{base_name}_part{i + 1}.mp4"
                clip = VideoFileClip(video_path).subclip(start, end)
                clip = self.crop_to_vertical(clip)

                titles = analysis.get("suggested_titles", [f"Amazing Part {i + 1}"])
                title = titles[min(i, len(titles) - 1)]
                clip = self.add_text_overlay(clip, title, position="center", fontsize=65)

                transcript = analysis.get("transcript", "")
                if transcript:
                    words = transcript.split()
                    segment_text = " ".join(words[i * 5 : (i + 1) * 5 + 10])
                    clip = self.add_captions(clip, segment_text)

                output_path = os.path.join(OUTPUT_FOLDER, output_name)
                self._export(clip, output_path, temp_tag=str(i))
                reels.append(output_path)
                clip.close()

            except Exception as e:
                print(f"[create_multiple_reels] Error on reel {i + 1}: {e}")
                continue

        return reels


if __name__ == "__main__":
    editor = VideoEditor()
    print("VideoEditor initialised successfully.")
    print(f"Output  folder : {OUTPUT_FOLDER}")
    print(f"Preview folder : {PREVIEW_FOLDER}")