"""
AI YouTube Automation - Main Orchestrator
Pipeline: Download → Analyze → Preview Reel → (approve) → Upload
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
from youtube_uploader import YouTubeUploader, setup_oauth_credentials
from video_downloader import VideoDownloader
from scheduler import AutomationScheduler, TaskLogger, logged_task


class AIYouTubeAutomation:
    """Main orchestrator for YouTube automation"""

    def __init__(self):
        self.analyzer = VideoAnalyzer()
        self.editor = VideoEditor()
        self.downloader = VideoDownloader()
        self.uploader = None
        self.scheduler = AutomationScheduler()

        os.makedirs(VIDEO_SOURCE_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(PREVIEW_FOLDER, exist_ok=True)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def check_setup(self, need_youtube: bool = True) -> bool:
        """
        FIX: Only require client_secrets.json when YouTube upload is needed.
        Download / Analyze / Create commands work without it.
        """
        issues = []

        if not GEMINI_API_KEY:
            issues.append("Gemini API key not set in .env file")

        if need_youtube and not os.path.exists("client_secrets.json"):
            issues.append(
                "client_secrets.json not found — needed only for YouTube upload. "
                "Run 'python main.py setup' for instructions."
            )

        if issues:
            print("\n⚠️  Setup issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False

        return True

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    @logged_task("Video Download")
    def download_trending(self, query: str = "trending", max_videos: int = 3) -> List[str]:
        print(f"\n🔍 Searching for: {query}")
        videos = self.downloader.search_and_download(query, max_results=max_videos)
        print(f"✅ Downloaded {len(videos)} videos")
        return videos

    @logged_task("Video Analysis")
    def analyze_video(self, video_path: str) -> dict:
        print(f"\n🤖 Analysing: {os.path.basename(video_path)}")
        analysis = self.analyzer.analyze_video_content(video_path)

        print(f"\n📊 Results:")
        print(f"   Topic        : {analysis.get('main_topic', 'N/A')}")
        print(f"   Virality     : {analysis.get('virality_score', 'N/A')}/10")
        print(f"   Sentiment    : {analysis.get('sentiment', 'N/A')}")
        print(f"   Hot words    : {', '.join(analysis.get('hot_words', [])[:5])}")
        return analysis

    @logged_task("Preview Reel")
    def create_preview(self, video_path: str, analysis: dict) -> Optional[str]:
        """
        FIX: Save reel to PREVIEW folder first — user verifies before upload.
        """
        print(f"\n✂️  Creating preview reel: {os.path.basename(video_path)}")
        preview = self.editor.create_preview_reel(video_path, analysis)
        if preview:
            print(f"\n👀 Preview saved → {preview}")
            print("   Watch this file, then run 'python main.py upload --video <path>' to publish.")
        return preview

    @logged_task("Video Editing")
    def create_reels(self, video_path: str, analysis: dict) -> List[str]:
        print(f"\n✂️  Creating reels: {os.path.basename(video_path)}")
        reels = self.editor.create_multiple_reels(video_path, analysis, max_reels=3)
        print(f"✅ Created {len(reels)} reels")
        return reels

    @logged_task("YouTube Upload")
    def upload_to_youtube(
        self, reel_path: str, analysis: dict, privacy: str = "private"
    ) -> Optional[dict]:
        if not self.uploader:
            print("\n🔐 Authenticating with YouTube…")
            self.uploader = YouTubeUploader()

        print(f"\n📤 Uploading: {os.path.basename(reel_path)}")
        result = self.uploader.upload_short(reel_path, analysis, privacy_status=privacy)

        if result:
            print(f"✅ Uploaded! Video ID: {result['id']}")
            print(f"   URL: https://youtube.com/shorts/{result['id']}")
        else:
            print("❌ Upload failed")
        return result

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def process_single_video(
        self, video_path: str, upload: bool = True, privacy: str = "private"
    ) -> List[dict]:
        results = []
        try:
            analysis = self.analyze_video(video_path)

            # Save analysis JSON
            analysis_file = os.path.join(
                OUTPUT_FOLDER, f"{Path(video_path).stem}_analysis.json"
            )
            with open(analysis_file, "w") as f:
                json.dump(analysis, f, indent=2)

            # Always create preview first
            preview = self.create_preview(video_path, analysis)
            if not preview:
                print("⚠️  Preview creation failed — skipping upload.")
                return []

            if upload:
                # Create final reels then upload
                reels = self.create_reels(video_path, analysis)
                for reel in reels:
                    res = self.upload_to_youtube(reel, analysis, privacy)
                    if res:
                        results.append({
                            "video": video_path,
                            "reel": reel,
                            "youtube_id": res["id"],
                            "url": f"https://youtube.com/shorts/{res['id']}",
                        })
            else:
                reels = self.create_reels(video_path, analysis)
                results = [{"reel": r} for r in reels]

            return results

        except Exception as e:
            TaskLogger.log_error("process_single_video", str(e))
            print(f"❌ Error: {e}")
            return []

    def process_local_videos(
        self, upload: bool = True, privacy: str = "private"
    ) -> List[dict]:
        videos = self.downloader.list_downloaded_videos()
        if not videos:
            print("No videos found in source folder.")
            return []

        print(f"\n📁 Found {len(videos)} videos")
        all_results = []
        for video in videos:
            results = self.process_single_video(video, upload, privacy)
            all_results.extend(results)
        return all_results

    @logged_task("Daily Automation")
    def run_daily_automation(self):
        print("\n" + "=" * 60)
        print("🤖 Daily AI YouTube Automation")
        print("=" * 60)
        try:
            existing = self.downloader.list_downloaded_videos()
            if not existing:
                print("\n📥 No local videos — downloading trending content…")
                topics = self.analyzer.get_trending_topics()
                for topic in topics[:2]:
                    self.download_trending(topic, max_videos=2)

            results = self.process_local_videos(upload=True, privacy="private")
            self.downloader.clean_old_downloads(keep_count=20)

            print("\n" + "=" * 60)
            print(f"✅ Done! Processed {len(results)} videos")
            print("=" * 60)
            return results

        except Exception as e:
            TaskLogger.log_error("daily_automation", str(e))
            print(f"❌ Daily automation failed: {e}")
            return []

    def start_scheduler(self, time: str = "09:00"):
        print(f"\n⏰ Scheduling daily run at {time}")
        self.scheduler.add_daily_job(self.run_daily_automation, time)
        self.scheduler.start_background(interval=60)
        print("Scheduler running. Press Ctrl+C to stop.")
        try:
            import time as _time
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping…")
            self.scheduler.stop()


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def print_help():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     🤖 AI YouTube Automation - Command Line Interface        ║
╚══════════════════════════════════════════════════════════════╝

COMMANDS:
  setup      Show setup instructions
  download   Download trending videos
  analyze    Analyse a specific video with Gemini
  preview    Create a preview reel (saved to output_reels/preview/)
  create     Create reels (saved to output_reels/, ready for upload)
  upload     Upload a reel to YouTube
  run        Full pipeline on all local videos (with preview step)
  schedule   Start daily automation scheduler
  test       Quick component smoke-test

OPTIONS:
  --video PATH       Path to video file
  --query TEXT       Search query for downloads
  --privacy LEVEL    private | unlisted | public  (default: private)
  --time HH:MM       Schedule time (default: 09:00)
  --max N            Max videos to download (default: 3)

TESTING WORKFLOW:
  1. python main.py test                            # smoke-test
  2. python main.py download --query "funny cats"   # download
  3. python main.py analyze  --video ./downloaded_videos/video.mp4
  4. python main.py preview  --video ./downloaded_videos/video.mp4
     # → watch output_reels/preview/preview_*.mp4
  5. python main.py create   --video ./downloaded_videos/video.mp4
  6. python main.py upload   --video ./output_reels/reel_*.mp4 --privacy private
""")


def main():
    parser = argparse.ArgumentParser(description="AI YouTube Automation")
    parser.add_argument(
        "command",
        choices=["setup", "download", "analyze", "preview", "create",
                 "upload", "run", "schedule", "test", "help"],
    )
    parser.add_argument("--video", help="Path to video file")
    parser.add_argument("--query", default="trending", help="Search query")
    parser.add_argument("--privacy", default="private",
                        choices=["private", "unlisted", "public"])
    parser.add_argument("--time", default="09:00")
    parser.add_argument("--max", type=int, default=3)

    args = parser.parse_args()

    if args.command == "help":
        print_help()
        return

    automation = AIYouTubeAutomation()

    # Commands that do NOT need YouTube credentials
    no_yt_commands = {"setup", "download", "analyze", "preview", "create", "test"}
    need_youtube = args.command not in no_yt_commands

    if args.command == "setup":
        print("\n" + "=" * 60)
        print("🛠️  Setup Guide")
        print("=" * 60)
        print("\n1. cp .env.example .env  → add GEMINI_API_KEY")
        print("2. Install deps: pip install -r requirements.txt")
        print("3. Install ffmpeg (brew / apt / ffmpeg.org)")
        setup_oauth_credentials()
        print("\n4. Test: python main.py test")
        return

    if not automation.check_setup(need_youtube=need_youtube):
        print("\nRun 'python main.py setup' for help.")
        return

    try:
        if args.command == "download":
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
            # Load analysis if JSON exists next to the video
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
            automation.process_local_videos(upload=True, privacy=args.privacy)

        elif args.command == "schedule":
            automation.start_scheduler(args.time)

        elif args.command == "test":
            print("\n🧪 Smoke test…")
            print("✓ Config loaded")
            print("✓ VideoAnalyzer  initialised")
            print("✓ VideoEditor    initialised")
            print("✓ VideoDownloader initialised")
            print("✓ AutomationScheduler initialised")
            print(f"\n   Source  : {VIDEO_SOURCE_FOLDER}")
            print(f"   Output  : {OUTPUT_FOLDER}")
            print(f"   Preview : {PREVIEW_FOLDER}")
            print("\n✅ All components OK")

    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()