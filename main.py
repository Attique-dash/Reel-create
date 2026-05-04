"""
AI YouTube Automation - Main Entry Point
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List

from config import VIDEO_SOURCE_FOLDER, OUTPUT_FOLDER, GEMINI_API_KEY
from video_analyzer import VideoAnalyzer
from video_editor import VideoEditor, PREVIEW_FOLDER
from video_downloader import VideoDownloader
from scheduler import AutomationScheduler, TaskLogger, logged_task


class AIYouTubeAutomation:
    def __init__(self):
        self.analyzer = VideoAnalyzer()
        self.editor = VideoEditor()
        self.downloader = VideoDownloader()
        self.uploader = None
        self.scheduler = AutomationScheduler()
        os.makedirs(VIDEO_SOURCE_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(PREVIEW_FOLDER, exist_ok=True)

    def check_setup(self, need_youtube: bool = False) -> bool:
        issues = []
        if not GEMINI_API_KEY:
            issues.append("GEMINI_API_KEY not set")
        if need_youtube and not os.path.exists("client_secrets.json"):
            issues.append("client_secrets.json not found")
        if issues:
            print("\n⚠️  Setup issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        return True

    @logged_task("Video Download")
    def download_trending(self, query: str = "trending", max_videos: int = 3) -> List[str]:
        print(f"\n🔍 Searching: {query}")
        videos = self.downloader.search_and_download(query, max_results=max_videos)
        print(f"✅ Downloaded {len(videos)} videos")
        return videos

    @logged_task("Video Analysis")
    def analyze_video(self, video_path: str) -> dict:
        print(f"\n🤖 Analysing: {os.path.basename(video_path)}")
        analysis = self.analyzer.analyze_video_content(video_path)
        print(f"\n📊 Results:")
        print(f"   Topic    : {analysis.get('main_topic', 'N/A')}")
        print(f"   Virality : {analysis.get('virality_score', 'N/A')}/10")
        print(f"   Sentiment: {analysis.get('sentiment', 'N/A')}")
        print(f"   Keywords : {', '.join(analysis.get('hot_words', [])[:5])}")
        return analysis

    @logged_task("Preview Reel")
    def create_preview(self, video_path: str, analysis: dict) -> Optional[str]:
        print(f"\n✂️  Creating preview: {os.path.basename(video_path)}")
        preview = self.editor.create_preview_reel(video_path, analysis)
        if preview:
            print(f"\n👀 Preview saved → {preview}")
        return preview

    @logged_task("Video Editing")
    def create_reels(self, video_path: str, analysis: dict) -> List[str]:
        print(f"\n✂️  Creating reels: {os.path.basename(video_path)}")
        reels = self.editor.create_multiple_reels(video_path, analysis, max_reels=3)
        print(f"✅ Created {len(reels)} reels")
        return reels

    @logged_task("YouTube Upload")
    def upload_to_youtube(self, reel_path: str, analysis: dict,
                          privacy: str = "private") -> Optional[dict]:
        from youtube_uploader import YouTubeUploader
        if not self.uploader:
            print("\n🔐 Authenticating YouTube...")
            self.uploader = YouTubeUploader()
        print(f"\n📤 Uploading: {os.path.basename(reel_path)}")
        result = self.uploader.upload_short(reel_path, analysis, privacy_status=privacy)
        if result:
            print(f"✅ Uploaded! URL: https://youtube.com/shorts/{result['id']}")
        else:
            print("❌ Upload failed")
        return result


def main():
    parser = argparse.ArgumentParser(description="AI YouTube Automation")
    parser.add_argument("command", choices=[
        "setup", "download", "analyze", "preview",
        "create", "upload", "run", "schedule", "test", "help"
    ])
    parser.add_argument("--video", help="Path to video file")
    parser.add_argument("--query", default="trending viral shorts")
    parser.add_argument("--privacy", default="private",
                        choices=["private", "unlisted", "public"])
    parser.add_argument("--time", default="09:00")
    parser.add_argument("--max", type=int, default=2)

    args = parser.parse_args()

    if args.command == "help":
        print("""
Commands:
  test      - Smoke test all components
  download  - Download trending videos
  analyze   - Analyze a video with Gemini
  preview   - Create preview reel
  create    - Create final reels
  upload    - Upload reel to YouTube
  run       - Full pipeline on all local videos
  schedule  - Start daily scheduler
        """)
        return

    automation = AIYouTubeAutomation()
    need_youtube = args.command in {"upload", "run"}

    if not automation.check_setup(need_youtube=need_youtube):
        return

    try:
        if args.command == "test":
            print("\n🧪 Smoke test...")
            print("✓ config.py loaded")
            print("✓ VideoAnalyzer ready")
            print("✓ VideoEditor ready")
            print("✓ VideoDownloader ready")
            print("✓ AutomationScheduler ready")
            print(f"\n   Source  : {VIDEO_SOURCE_FOLDER}")
            print(f"   Output  : {OUTPUT_FOLDER}")
            print(f"   Preview : {PREVIEW_FOLDER}")
            print("\n✅ All components OK")

        elif args.command == "download":
            automation.download_trending(args.query, args.max)

        elif args.command == "analyze":
            if not args.video:
                print("❌ Provide --video path")
                return
            automation.analyze_video(args.video)

        elif args.command == "preview":
            if not args.video:
                print("❌ Provide --video path")
                return
            analysis = automation.analyze_video(args.video)
            automation.create_preview(args.video, analysis)

        elif args.command == "create":
            if not args.video:
                print("❌ Provide --video path")
                return
            analysis = automation.analyze_video(args.video)
            automation.create_reels(args.video, analysis)

        elif args.command == "upload":
            if not args.video:
                print("❌ Provide --video path")
                return
            analysis_path = args.video.rsplit(".", 1)[0] + "_analysis.json"
            if os.path.exists(analysis_path):
                with open(analysis_path) as f:
                    analysis = json.load(f)
            else:
                analysis = {
                    "suggested_titles": [Path(args.video).stem],
                    "suggested_description": "Check this out!",
                    "tags": ["#shorts", "#viral"],
                    "hot_words": ["trending"],
                    "main_topic": "Entertainment",
                }
            automation.upload_to_youtube(args.video, analysis, args.privacy)

        elif args.command == "run":
            videos = automation.downloader.list_downloaded_videos()
            if not videos:
                print("No videos in downloaded_videos/ folder.")
                return
            print(f"\n📁 Found {len(videos)} videos")
            for video in videos:
                analysis = automation.analyze_video(video)
                analysis_file = os.path.join(
                    OUTPUT_FOLDER, f"{Path(video).stem[:40]}_analysis.json")
                with open(analysis_file, "w") as f:
                    json.dump(analysis, f, indent=2)
                reels = automation.create_reels(video, analysis)
                for reel in reels:
                    automation.upload_to_youtube(reel, analysis, args.privacy)

        elif args.command == "schedule":
            def daily_job():
                videos = automation.downloader.list_downloaded_videos()
                if not videos:
                    automation.download_trending("trending viral shorts", 2)
                    videos = automation.downloader.list_downloaded_videos()
                for video in videos:
                    analysis = automation.analyze_video(video)
                    reels = automation.create_reels(video, analysis)
                    for reel in reels:
                        automation.upload_to_youtube(reel, analysis, "private")

            print(f"\n⏰ Scheduling daily run at {args.time}")
            automation.scheduler.add_daily_job(daily_job, args.time)
            automation.scheduler.start_background()
            print("Running. Press Ctrl+C to stop.")
            try:
                import time as _time
                while True:
                    _time.sleep(1)
            except KeyboardInterrupt:
                automation.scheduler.stop()

    except KeyboardInterrupt:
        print("\n⚠️  Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()