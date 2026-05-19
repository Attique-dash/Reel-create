"""
AI YouTube Automation — content queue → AI Short → optional upload.
"""
import os
import json
import glob
import argparse
from pathlib import Path
from typing import Optional

from config import (
    GEMINI_API_KEY,
    AUTO_UPLOAD,
    TIP_NICHE,
    TTS_VOICE,
    CHANNEL_NAME,
    CONTENT_QUEUE_FILE,
    QUEUE_OUTPUT_FOLDER,
    UPLOAD_TIME_1,
    UPLOAD_TIME_2,
)
from scheduler import AutomationScheduler, logged_task


class AIYouTubeAutomation:
    def __init__(self):
        self.uploader = None
        self.scheduler = AutomationScheduler()
        os.makedirs(QUEUE_OUTPUT_FOLDER, exist_ok=True)

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

    @logged_task("YouTube Upload")
    def upload_to_youtube(self, video_path: str, analysis: dict,
                          privacy: str = "private") -> Optional[dict]:
        from youtube_uploader import YouTubeUploader
        if not self.uploader:
            print("\n🔐 Authenticating YouTube...")
            self.uploader = YouTubeUploader()
        print(f"\n📤 Uploading: {os.path.basename(video_path)}")
        result = self.uploader.upload_short(video_path, analysis, privacy_status=privacy)
        if result:
            print(f"✅ Uploaded! URL: https://youtube.com/shorts/{result['id']}")
        else:
            print("❌ Upload failed")
        return result

    @logged_task("Queue Video")
    def create_queue_video(
        self,
        content_file: Optional[str] = None,
        topic: Optional[str] = None,
        upload: bool = False,
        privacy: str = "private",
        slot: Optional[str] = None,
    ) -> dict:
        from queue_shorts import QueueVideoPipeline
        pipeline = QueueVideoPipeline(content_file=content_file or CONTENT_QUEUE_FILE)
        return pipeline.run(
            topic=topic,
            upload=upload,
            privacy=privacy,
            uploader=self.uploader,
            slot=slot,
        )

    def show_queue_status(self, content_file: Optional[str] = None) -> dict:
        from content_queue import ContentQueue
        q = ContentQueue(file_path=content_file or CONTENT_QUEUE_FILE)
        st = q.status()
        print(f"\n📋 Content queue: {st['file']}")
        print(f"   Total topics : {st['total']}")
        print(f"   Used         : {st['used']}")
        print(f"   Remaining    : {st['remaining']}")
        if st["remaining"] and st["remaining"] <= 10:
            print("\n   Unused topics:")
            for i in st["unused_indices"]:
                print(f"      {i + 1}. {st['lines'][i]}")
        return st

    def _analysis_for_video(self, video_path: str) -> dict:
        """Load sidecar JSON from queue folder, or minimal defaults."""
        stem = Path(video_path).stem
        folder = Path(video_path).parent
        for pattern in (f"{stem}.json", f"{stem}_*.json"):
            for path in folder.glob(pattern):
                try:
                    with open(path, encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue
        for path in glob.glob(os.path.join(QUEUE_OUTPUT_FOLDER, "*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("queue_topic"):
                    return data
            except Exception:
                continue
        return {
            "suggested_titles": [stem.replace("_", " ")[:60] + " #Shorts"],
            "suggested_description": "Daily Short — follow for more tips.",
            "tags": ["#shorts", "#tips"],
            "hot_words": ["tips"],
            "main_topic": "Education",
        }


def run_smoke_test():
    import shutil
    print("\n🧪 Smoke test...")
    print(f"   GEMINI_API_KEY : {'set' if GEMINI_API_KEY else 'MISSING'}")
    print(f"   AUTO_UPLOAD    : {AUTO_UPLOAD}")
    print(f"   Queue folder   : {QUEUE_OUTPUT_FOLDER}")
    print(f"   Content file   : {CONTENT_QUEUE_FILE}")
    print(f"   Upload times   : {UPLOAD_TIME_1} & {UPLOAD_TIME_2} (2/day)")
    print(f"   TTS voice      : {TTS_VOICE}")
    print(f"   Channel name   : {CHANNEL_NAME}")
    print(f"   Tip niche      : {TIP_NICHE}")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            print(f"✓ {tool} found")
        else:
            print(f"⚠️  {tool} not found — install: brew install ffmpeg")
    if os.path.exists("client_secrets.json"):
        print("✓ client_secrets.json found")
    else:
        print("⚠️  client_secrets.json missing (needed for YouTube upload)")
    os.makedirs(QUEUE_OUTPUT_FOLDER, exist_ok=True)
    try:
        import edge_tts  # noqa: F401
        print("✓ edge-tts installed")
    except ImportError:
        print("⚠️  edge-tts missing — run: pip install -r requirements.txt")
    print("\n✅ Setup OK — python main.py queue-video --no-upload")


def main():
    parser = argparse.ArgumentParser(description="AI YouTube Shorts from topic queue")
    parser.add_argument("command", choices=[
        "test", "help", "queue-video", "queue-status",
        "schedule-queue", "upload",
    ])
    parser.add_argument("--content-file", default=None,
                        help="Topics .txt (one line per video)")
    parser.add_argument("--topic", default=None,
                        help="Fixed topic instead of random line")
    parser.add_argument("--reset-queue", action="store_true",
                        help="Reset used-line tracking")
    parser.add_argument("--video", help="MP4 path (for upload)")
    parser.add_argument("--privacy", default="private",
                        choices=["private", "unlisted", "public"])
    parser.add_argument("--upload", action="store_true",
                        help="Upload to YouTube after creating")
    parser.add_argument("--no-upload", action="store_true",
                        help="Save video only")

    args = parser.parse_args()

    if args.command == "help":
        print("""
Commands:
  test           - Check API keys, ffmpeg, edge-tts
  queue-status   - Topics used / remaining (--reset-queue to start over)
  queue-video    - Random unused line → AI Short → output_reels/queue/
  schedule-queue - 2 videos/day at UPLOAD_TIME_1 & UPLOAD_TIME_2 (.env)
  upload         - Upload existing MP4 (--video path)

Workflow:
  1. Edit content/video_topics.txt (one topic per line)
  2. python main.py queue-video --no-upload
  3. python main.py queue-video --upload --privacy private
  4. python main.py schedule-queue --upload
        """)
        return

    if args.command == "test":
        run_smoke_test()
        return

    automation = AIYouTubeAutomation()
    do_upload = args.upload or (AUTO_UPLOAD and not args.no_upload)
    need_youtube = args.command == "upload" or (
        do_upload and args.command in {"schedule-queue", "queue-video"}
    )

    if not automation.check_setup(need_youtube=need_youtube):
        return

    try:
        if args.command == "queue-status":
            if args.reset_queue:
                from content_queue import ContentQueue
                ContentQueue(file_path=args.content_file or CONTENT_QUEUE_FILE).reset()
                print("✅ Queue reset — all lines available again.")
            automation.show_queue_status(content_file=args.content_file)

        elif args.command == "queue-video":
            result = automation.create_queue_video(
                content_file=args.content_file,
                topic=args.topic,
                upload=do_upload,
                privacy=args.privacy,
            )
            print(f"\n✅ Video ready → {result['video_path']}")
            print(f"   Topic: {result['topic']}")
            if result.get("uploaded"):
                print(f"   YouTube ID: {result.get('youtube_id')}")

        elif args.command == "upload":
            if not args.video:
                print("❌ Provide --video path")
                return
            analysis = automation._analysis_for_video(args.video)
            automation.upload_to_youtube(args.video, analysis, args.privacy)

        elif args.command == "schedule-queue":
            def queue_job_morning():
                automation.create_queue_video(
                    content_file=args.content_file,
                    upload=do_upload or AUTO_UPLOAD,
                    privacy=args.privacy,
                    slot="am",
                )

            def queue_job_evening():
                automation.create_queue_video(
                    content_file=args.content_file,
                    upload=do_upload or AUTO_UPLOAD,
                    privacy=args.privacy,
                    slot="pm",
                )

            print(f"\n⏰ Scheduling 2 videos per day:")
            print(f"   Morning: {UPLOAD_TIME_1}")
            print(f"   Evening: {UPLOAD_TIME_2}")
            automation.scheduler.add_daily_job(queue_job_morning, UPLOAD_TIME_1)
            automation.scheduler.add_daily_job(queue_job_evening, UPLOAD_TIME_2)
            automation.scheduler.start_background()
            print("Running. Press Ctrl+C to stop.")
            try:
                import time
                while True:
                    time.sleep(1)
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
