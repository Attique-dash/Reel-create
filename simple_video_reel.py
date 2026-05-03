#!/usr/bin/env python3
"""
Simple Video Reel Creator
Download a video from URL and create a YouTube Short/Reel
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def download_video(url: str, output_folder: str = "./videos") -> str:
    """Download video using yt-dlp"""
    print(f"📥 Downloading video from: {url}")
    os.makedirs(output_folder, exist_ok=True)
    
    # yt-dlp command to download best quality video
    cmd = [
        "yt-dlp",
        "-f", "best[height<=1080]",
        "--no-playlist",
        "-o", f"{output_folder}/%(title)s.%(ext)s",
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Find the downloaded file
        files = list(Path(output_folder).glob("*.*"))
        video_files = [f for f in files if f.suffix in ['.mp4', '.mkv', '.webm']]
        
        if video_files:
            # Get most recent file
            video_path = str(max(video_files, key=lambda p: p.stat().st_mtime))
            print(f"✅ Downloaded: {os.path.basename(video_path)}")
            return video_path
        else:
            print("❌ Could not find downloaded video")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")
        print(f"Error: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ yt-dlp not found. Install with: pip install yt-dlp")
        return None


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 0


def create_reel(video_path: str, start_time: int = 0, duration: int = 30, 
                output_folder: str = "./reels") -> str:
    """Create a vertical reel from video using ffmpeg"""
    print(f"✂️  Creating reel from: {os.path.basename(video_path)}")
    os.makedirs(output_folder, exist_ok=True)
    
    # Output filename
    base_name = Path(video_path).stem
    output_path = os.path.join(output_folder, f"reel_{base_name}.mp4")
    
    # Get video info
    video_duration = get_video_duration(video_path)
    if video_duration == 0:
        print("❌ Could not read video duration")
        return None
    
    # Adjust start time if needed
    if start_time >= video_duration:
        start_time = 0
    
    max_duration = min(duration, int(video_duration - start_time))
    
    print(f"   Segment: {start_time}s to {start_time + max_duration}s")
    print(f"   Output: {output_path}")
    
    # ffmpeg command to create vertical reel
    # - Crops to 9:16 aspect ratio (1080x1920)
    # - Takes segment from start_time for max_duration
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-ss", str(start_time),           # Start time
        "-t", str(max_duration),          # Duration
        "-vf", "crop=ih*9/16:ih,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",  # Overwrite output
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024*1024)  # MB
            print(f"✅ Reel created: {output_path} ({file_size:.1f} MB)")
            return output_path
        else:
            print("❌ Reel creation failed")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")
        print("Make sure ffmpeg is installed:")
        print("  Mac: brew install ffmpeg")
        print("  Linux: sudo apt-get install ffmpeg")
        return None
    except FileNotFoundError:
        print("❌ ffmpeg not found. Please install ffmpeg first.")
        return None


def main():
    parser = argparse.ArgumentParser(description="Download video and create reel")
    parser.add_argument("url", help="Video URL to download")
    parser.add_argument("--start", type=int, default=0, 
                       help="Start time in seconds (default: 0)")
    parser.add_argument("--duration", type=int, default=30,
                       help="Reel duration in seconds (default: 30)")
    parser.add_argument("--output", default="./reels",
                       help="Output folder for reels")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🎬 Simple Video Reel Creator")
    print("=" * 50)
    
    # Step 1: Download video
    video_path = download_video(args.url)
    if not video_path:
        print("\n❌ Failed to download video")
        sys.exit(1)
    
    # Step 2: Create reel
    reel_path = create_reel(
        video_path, 
        start_time=args.start,
        duration=args.duration,
        output_folder=args.output
    )
    
    if reel_path:
        print("\n" + "=" * 50)
        print("🎉 Success!")
        print(f"📹 Original: {video_path}")
        print(f"🎬 Reel: {reel_path}")
        print("=" * 50)
    else:
        print("\n❌ Failed to create reel")
        sys.exit(1)


if __name__ == "__main__":
    main()
