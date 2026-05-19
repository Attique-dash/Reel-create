"""
AI YouTube Automation - Main Entry Point
"""
import os
import sys
import json
import glob
import time
import hashlib
import argparse
from pathlib import Path
from typing import Optional, List

from config import (
    VIDEO_SOURCE_FOLDER, OUTPUT_FOLDER, GEMINI_API_KEY, AUTO_UPLOAD,
    TIP_NICHE, TIPS_OUTPUT_FOLDER, TTS_VOICE, CHANNEL_NAME,
)
from video_analyzer import VideoAnalyzer
from video_editor import VideoEditor, PREVIEW_FOLDER
from video_downloader import VideoDownloader
from scheduler import AutomationScheduler, TaskLogger, logged_task


class AIYouTubeAutomation:
    PROCESSED_LOG = os.path.join(OUTPUT_FOLDER, ".processed_videos.json")

    def __init__(self):
        self.analyzer = VideoAnalyzer()
        self.editor = VideoEditor()
        self.downloader = VideoDownloader()
        self.uploader = None
        self.scheduler = AutomationScheduler()
        self._processed_videos = self._load_processed_log()
        os.makedirs(VIDEO_SOURCE_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(PREVIEW_FOLDER, exist_ok=True)

    def _load_processed_log(self) -> dict:
        """Load the log of processed videos to avoid duplicates."""
        if os.path.exists(self.PROCESSED_LOG):
            try:
                with open(self.PROCESSED_LOG, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_processed_log(self):
        """Save the processed videos log."""
        try:
            with open(self.PROCESSED_LOG, "w") as f:
                json.dump(self._processed_videos, f, indent=2)
        except Exception as e:
            print(f"[Warning] Could not save processed log: {e}")

    def _get_video_hash(self, video_path: str) -> str:
        """Generate a unique hash for a video file."""
        import hashlib
        stat = os.stat(video_path)
        # Use file path, size, and mtime for uniqueness
        hash_input = f"{video_path}:{stat.st_size}:{stat.st_mtime}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    def is_video_processed(self, video_path: str) -> bool:
        """Check if a video has already been processed."""
        if not os.path.exists(video_path):
            return False
        video_hash = self._get_video_hash(video_path)
        return video_hash in self._processed_videos

    def mark_video_processed(self, video_path: str, reels: list = None, uploaded: bool = False):
        """Mark a video as processed with metadata."""
        video_hash = self._get_video_hash(video_path)
        self._processed_videos[video_hash] = {
            "path": video_path,
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reels": reels or [],
            "uploaded": uploaded
        }
        self._save_processed_log()

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

    def process_local_videos(self, upload: bool = False, privacy: str = "private",
                             max_reels: int = 3) -> int:
        """Analyze videos in VIDEO_SOURCE_FOLDER, create reels, optionally upload."""
        videos = self.downloader.list_downloaded_videos()
        if not videos:
            print(f"\n📁 No videos in {VIDEO_SOURCE_FOLDER}/")
            print(f"   Drop .mp4 files there, or run: python main.py download")
            return 0

        new_videos = [v for v in videos if not self.is_video_processed(v)]
        skipped = len(videos) - len(new_videos)
        if skipped:
            print(f"\n📁 {len(videos)} videos ({skipped} already done, {len(new_videos)} new)")
        else:
            print(f"\n📁 Processing {len(videos)} video(s) from {VIDEO_SOURCE_FOLDER}/")

        if not new_videos:
            print("✅ All videos already processed.")
            return 0

        processed = 0
        for video in new_videos:
            analysis = self.analyze_video(video)
            analysis_file = os.path.join(
                OUTPUT_FOLDER, f"{Path(video).stem[:40]}_analysis.json")
            with open(analysis_file, "w") as f:
                json.dump(analysis, f, indent=2)
            print(f"   💾 Analysis saved → {analysis_file}")

            reels = self.create_reels(video, analysis)
            if not reels:
                print(f"   ⚠️  No reels created for {os.path.basename(video)}")
                continue

            print(f"\n   📂 Reels in {OUTPUT_FOLDER}/:")
            for reel in reels:
                print(f"      • {os.path.basename(reel)}")

            uploaded = False
            if upload:
                for reel in reels:
                    result = self.upload_to_youtube(reel, analysis, privacy)
                    if result:
                        uploaded = True
            else:
                print("   (Upload skipped — use --upload or AUTO_UPLOAD=true)")

            self.mark_video_processed(video, reels, uploaded)
            processed += 1

        return processed

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

    @logged_task("Daily Tip Short")
    def create_daily_tip(self, niche: Optional[str] = None, upload: bool = False,
                         privacy: str = "private") -> dict:
        from tip_shorts import DailyTipPipeline
        pipeline = DailyTipPipeline(niche=niche or TIP_NICHE)
        return pipeline.run(upload=upload, privacy=privacy, uploader=self.uploader)


def run_smoke_test():
    import shutil
    print("\n🧪 Smoke test...")
    print("✓ config.py loaded")
    print(f"   GEMINI_API_KEY : {'set' if GEMINI_API_KEY else 'MISSING'}")
    print(f"   AUTO_UPLOAD    : {AUTO_UPLOAD}")
    print(f"   Source folder  : {VIDEO_SOURCE_FOLDER}")
    print(f"   Output folder  : {OUTPUT_FOLDER}")
    print(f"   Tip niche      : {TIP_NICHE}")
    print(f"   Tips folder    : {TIPS_OUTPUT_FOLDER}")
    print(f"   TTS voice      : {TTS_VOICE}")
    print(f"   Channel name   : {CHANNEL_NAME}")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            print(f"✓ {tool} found")
        else:
            print(f"⚠️  {tool} not found — install: brew install ffmpeg")
    if os.path.exists("client_secrets.json"):
        print("✓ client_secrets.json found")
    else:
        print("⚠️  client_secrets.json missing (needed for YouTube upload)")
    os.makedirs(VIDEO_SOURCE_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    try:
        import edge_tts  # noqa: F401
        print("✓ edge-tts installed (Idea 2 TTS)")
    except ImportError:
        print("⚠️  edge-tts missing — run: pip install edge-tts")
    print("\n✅ Setup check complete.")
    print("   Clip pipeline : python main.py process")
    print("   Daily tip     : python main.py daily-tip --no-upload")


def main():
    parser = argparse.ArgumentParser(description="AI YouTube Automation")
    parser.add_argument("command", choices=[
        "setup", "download", "analyze", "preview",
        "create", "upload", "process", "run", "full",
        "daily-tip", "schedule", "test", "help"
    ])
    parser.add_argument("--niche", default=None,
                        help="Niche for daily-tip (overrides TIP_NICHE in .env)")
    parser.add_argument("--video", help="Path to video file")
    parser.add_argument("--query", default="trending viral shorts")
    parser.add_argument("--privacy", default="private",
                        choices=["private", "unlisted", "public"])
    parser.add_argument("--time", default="09:00")
    parser.add_argument("--max", type=int, default=2)
    parser.add_argument("--download", action="store_true",
                        help="Download trending videos before processing (run/full)")
    parser.add_argument("--upload", action="store_true",
                        help="Upload reels to YouTube after creating them")
    parser.add_argument("--no-upload", action="store_true",
                        help="Only save reels to output folder (no YouTube)")

    args = parser.parse_args()

    if args.command == "help":
        print("""
Commands:
  test      - Smoke test all components
  download  - Download trending videos into downloaded_videos/
  analyze   - Extract hot words & metadata (Gemini)
  preview   - One preview reel in output_reels/preview/
  create    - Up to 3 Shorts reels in output_reels/
  upload    - Upload one reel to YouTube
  process   - Process all videos in downloaded_videos/ → reels (no download)
  run       - Same as process (alias); use --download / --upload flags
  full      - Download trending, then process + optional upload
  schedule  - Daily: download if empty, process, upload
  daily-tip - Idea 2: original English tip → TTS → faceless Short (see --niche)

Workflow (clip existing videos):
  1. Put videos in downloaded_videos/  OR  python main.py download
  2. python main.py process              → reels + *_analysis.json in output_reels/
  3. python main.py upload --video ...   → YouTube (or use --upload on process/run)

Workflow (Idea 2 — daily original tip):
  1. python main.py daily-tip --no-upload   → output_reels/tips/tip_YYYY-MM-DD.mp4
  2. python main.py daily-tip --upload      → same + YouTube (private by default)
  3. GitHub Actions cron can run daily-tip once per day
        """)
        return

    if args.command == "test":
        run_smoke_test()
        return

    automation = AIYouTubeAutomation()
    do_upload = args.upload or (AUTO_UPLOAD and not args.no_upload)
    if args.command in {"run", "full", "schedule"} and not args.no_upload and not args.upload:
        do_upload = do_upload or AUTO_UPLOAD
    need_youtube = args.command == "upload" or (
        do_upload and args.command in {"run", "full", "process", "schedule", "daily-tip"}
    )

    if not automation.check_setup(need_youtube=need_youtube):
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
            # Look for analysis JSON - reels have different naming than source videos
            analysis = None
            video_stem = Path(args.video).stem
            # Try exact match first (consistent 40-char truncation used by run command)
            truncated_stem = video_stem[:40]
            analysis_path = os.path.join(OUTPUT_FOLDER, f"{truncated_stem}_analysis.json")
            if not os.path.exists(analysis_path):
                # Try non-truncated version as fallback
                analysis_path = os.path.join(OUTPUT_FOLDER, f"{video_stem}_analysis.json")
            if os.path.exists(analysis_path):
                with open(analysis_path) as f:
                    analysis = json.load(f)
            else:
                # Try to find any analysis JSON that might match this reel
                # Reels are named like: reel_<source>_part1.mp4 or reel_<source>_<start>_<end>.mp4
                json_files = glob.glob(os.path.join(OUTPUT_FOLDER, "*_analysis.json"))
                for json_file in json_files:
                    try:
                        with open(json_file) as f:
                            candidate = json.load(f)
                        # Use first available analysis if no direct match
                        analysis = candidate
                        break
                    except Exception:
                        continue
            if not analysis:
                analysis = {
                    "suggested_titles": [video_stem],
                    "suggested_description": "Check this out!",
                    "tags": ["#shorts", "#viral"],
                    "hot_words": ["trending"],
                    "main_topic": "Entertainment",
                }
            automation.upload_to_youtube(args.video, analysis, args.privacy)

        elif args.command in ("process", "run"):
            if args.download:
                automation.download_trending(args.query, args.max)
            count = automation.process_local_videos(
                upload=do_upload, privacy=args.privacy)
            if count:
                print(f"\n✅ Done. Processed {count} video(s).")
                print(f"   Reels → {OUTPUT_FOLDER}/")

        elif args.command == "full":
            automation.download_trending(args.query, args.max)
            count = automation.process_local_videos(
                upload=do_upload, privacy=args.privacy)
            if count:
                print(f"\n✅ Full pipeline done ({count} video(s)).")

        elif args.command == "daily-tip":
            result = automation.create_daily_tip(
                niche=args.niche,
                upload=do_upload,
                privacy=args.privacy,
            )
            print(f"\n✅ Daily tip ready → {result['video_path']}")
            if result.get("uploaded"):
                print(f"   YouTube ID: {result.get('youtube_id')}")

        elif args.command == "schedule":
            def daily_job():
                automation.create_daily_tip(
                    niche=args.niche,
                    upload=AUTO_UPLOAD or do_upload,
                    privacy="private",
                )

            print(f"\n⏰ Scheduling daily tip (Idea 2) at {args.time}")
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