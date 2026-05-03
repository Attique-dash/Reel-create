"""
AI YouTube Automation - Main Orchestrator
This is the main entry point for the AI YouTube automation system.

Features:
- Download trending videos OR use local videos
- AI analysis to extract hot words and trending topics
- Automatic video editing to create Shorts/Reels
- Upload to YouTube with optimized metadata
- Daily scheduling for automation
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List

# Import modules
from config import VIDEO_SOURCE_FOLDER, OUTPUT_FOLDER, GEMINI_API_KEY
from video_analyzer import VideoAnalyzer
from video_editor import VideoEditor
from youtube_uploader import YouTubeUploader, setup_oauth_credentials
from video_downloader import VideoDownloader
from scheduler import AutomationScheduler, TaskLogger, logged_task


class AIYouTubeAutomation:
    """Main orchestrator for YouTube automation"""
    
    def __init__(self):
        self.analyzer = VideoAnalyzer()
        self.editor = VideoEditor()
        self.downloader = VideoDownloader()
        self.uploader = None  # Initialized when needed
        self.scheduler = AutomationScheduler()
        
        # Ensure directories exist
        os.makedirs(VIDEO_SOURCE_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    def check_setup(self) -> bool:
        """Check if all necessary setup is complete"""
        issues = []
        
        if not GEMINI_API_KEY:
            issues.append("Gemini API key not set in .env file")
        
        if not os.path.exists("client_secrets.json"):
            issues.append("client_secrets.json not found (needed for YouTube upload)")
        
        if issues:
            print("\n⚠️  Setup issues found:")
            for issue in issues:
                print(f"   - {issue}")
            print("\nPlease fix these issues before continuing.")
            return False
        
        return True
    
    @logged_task("Video Download")
    def download_trending(self, query: str = "trending", max_videos: int = 3) -> List[str]:
        """Download trending videos"""
        print(f"\n🔍 Searching for: {query}")
        videos = self.downloader.search_and_download(query, max_results=max_videos)
        print(f"✅ Downloaded {len(videos)} videos")
        return videos
    
    @logged_task("Video Analysis")
    def analyze_video(self, video_path: str) -> dict:
        """Analyze video content using AI"""
        print(f"\n🤖 Analyzing video: {os.path.basename(video_path)}")
        analysis = self.analyzer.analyze_video_content(video_path)
        
        print(f"\n📊 Analysis Results:")
        print(f"   Main Topic: {analysis.get('main_topic', 'N/A')}")
        print(f"   Virality Score: {analysis.get('virality_score', 'N/A')}/10")
        print(f"   Sentiment: {analysis.get('sentiment', 'N/A')}")
        print(f"   Hot Words: {', '.join(analysis.get('hot_words', [])[:5])}")
        
        return analysis
    
    @logged_task("Video Editing")
    def create_reels(self, video_path: str, analysis: dict) -> List[str]:
        """Create Shorts/Reels from video"""
        print(f"\n✂️  Creating reels from: {os.path.basename(video_path)}")
        reels = self.editor.create_multiple_reels(video_path, analysis, max_reels=3)
        print(f"✅ Created {len(reels)} reels")
        return reels
    
    @logged_task("YouTube Upload")
    def upload_to_youtube(self, reel_path: str, analysis: dict, 
                          privacy: str = "private") -> Optional[dict]:
        """Upload reel to YouTube"""
        # Initialize uploader if needed
        if not self.uploader:
            print("\n🔐 Authenticating with YouTube...")
            self.uploader = YouTubeUploader()
        
        print(f"\n📤 Uploading: {os.path.basename(reel_path)}")
        result = self.uploader.upload_short(reel_path, analysis, privacy_status=privacy)
        
        if result:
            print(f"✅ Upload successful! Video ID: {result['id']}")
            return result
        else:
            print("❌ Upload failed")
            return None
    
    def process_single_video(self, video_path: str, upload: bool = True,
                            privacy: str = "private") -> List[str]:
        """Process a single video through the full pipeline"""
        results = []
        
        try:
            # Step 1: Analyze
            analysis = self.analyze_video(video_path)
            
            # Save analysis for reference
            analysis_file = os.path.join(
                OUTPUT_FOLDER, 
                f"{Path(video_path).stem}_analysis.json"
            )
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            # Step 2: Create reels
            reels = self.create_reels(video_path, analysis)
            
            # Step 3: Upload (if requested)
            if upload and reels:
                for reel in reels:
                    upload_result = self.upload_to_youtube(reel, analysis, privacy)
                    if upload_result:
                        results.append({
                            "video": video_path,
                            "reel": reel,
                            "youtube_id": upload_result['id'],
                            "url": f"https://youtube.com/shorts/{upload_result['id']}"
                        })
            else:
                results = [{"reel": r} for r in reels]
            
            return results
            
        except Exception as e:
            TaskLogger.log_error("process_single_video", str(e))
            print(f"❌ Error processing video: {e}")
            return []
    
    def process_local_videos(self, upload: bool = True, privacy: str = "private") -> List[dict]:
        """Process all videos in the source folder"""
        videos = self.downloader.list_downloaded_videos()
        
        if not videos:
            print("No videos found in source folder")
            return []
        
        print(f"\n📁 Found {len(videos)} videos to process")
        
        all_results = []
        for video in videos:
            results = self.process_single_video(video, upload, privacy)
            all_results.extend(results)
        
        return all_results
    
    @logged_task("Daily Automation")
    def run_daily_automation(self):
        """Complete daily automation workflow"""
        print("\n" + "="*60)
        print("🤖 Starting Daily AI YouTube Automation")
        print("="*60)
        
        try:
            # Step 1: Check for videos
            existing_videos = self.downloader.list_downloaded_videos()
            
            if not existing_videos:
                print("\n📥 No videos found. Downloading trending content...")
                trending_topics = self.analyzer.get_trending_topics()
                print(f"Trending topics: {trending_topics[:3]}")
                
                # Download videos for trending topics
                for topic in trending_topics[:2]:
                    self.download_trending(topic, max_videos=2)
            
            # Step 2: Process all videos
            results = self.process_local_videos(upload=True, privacy="private")
            
            # Step 3: Clean old downloads
            self.downloader.clean_old_downloads(keep_count=20)
            
            print("\n" + "="*60)
            print(f"✅ Daily automation complete! Processed {len(results)} videos")
            print("="*60)
            
            return results
            
        except Exception as e:
            TaskLogger.log_error("daily_automation", str(e))
            print(f"❌ Daily automation failed: {e}")
            return []
    
    def start_scheduler(self, time: str = "09:00"):
        """Start the daily automation scheduler"""
        print(f"\n⏰ Starting daily scheduler (runs at {time})")
        
        # Add daily job
        self.scheduler.add_daily_job(self.run_daily_automation, time)
        
        # Start in background
        self.scheduler.start_background(interval=60)
        
        print("\nScheduler is running. Press Ctrl+C to stop.")
        print("Logs are being written to automation_log.txt")
        
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping scheduler...")
            self.scheduler.stop()


def print_help():
    """Print help information"""
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║     🤖 AI YouTube Automation - Command Line Interface        ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
    python main.py [command] [options]

COMMANDS:
    setup          Show setup instructions and requirements
    download       Download trending videos
    analyze        Analyze a specific video
    create         Create reels from a video
    upload         Upload a reel to YouTube
    run            Run full pipeline on local videos
    schedule       Start daily automation scheduler
    test           Run a test of all components

OPTIONS:
    --video PATH   Path to video file
    --query TEXT   Search query for downloads
    --privacy      Privacy setting (private/unlisted/public)
    --time HH:MM   Schedule time (default: 09:00)

EXAMPLES:
    # Setup and check requirements
    python main.py setup
    
    # Download trending videos
    python main.py download --query "viral funny videos"
    
    # Analyze a video
    python main.py analyze --video ./downloaded_videos/myvideo.mp4
    
    # Create reels from video
    python main.py create --video ./downloaded_videos/myvideo.mp4
    
    # Upload a reel
    python main.py upload --video ./output_reels/reel_myvideo.mp4
    
    # Run full pipeline on all local videos
    python main.py run --privacy private
    
    # Start daily automation at 10:30 AM
    python main.py schedule --time 10:30

FILES:
    config.py              Configuration settings
    video_analyzer.py      AI video analysis
    video_editor.py        Video editing for Shorts/Reels
    youtube_uploader.py    YouTube upload functionality
    video_downloader.py    Video downloading from platforms
    scheduler.py           Daily automation scheduling
    
LOGS:
    automation_log.txt     Execution logs
    
SUPPORT:
    Make sure you have:
    1. Gemini API key in .env file
    2. client_secrets.json for YouTube API
    3. ffmpeg installed (for video processing)
    """
    print(help_text)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI YouTube Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "command",
        choices=["setup", "download", "analyze", "create", "upload", 
                "run", "schedule", "test", "help"],
        help="Command to run"
    )
    parser.add_argument("--video", help="Path to video file")
    parser.add_argument("--query", default="trending", help="Search query")
    parser.add_argument("--privacy", default="private",
                       choices=["private", "unlisted", "public"],
                       help="YouTube privacy setting")
    parser.add_argument("--time", default="09:00", help="Schedule time (HH:MM)")
    parser.add_argument("--max", type=int, default=3, help="Max videos to process")
    
    args = parser.parse_args()
    
    # Show help
    if args.command == "help":
        print_help()
        return
    
    # Initialize automation
    automation = AIYouTubeAutomation()
    
    # Setup command
    if args.command == "setup":
        print("\n" + "="*60)
        print("🛠️  AI YouTube Automation - Setup Guide")
        print("="*60)
        
        print("\n1. Create .env file with your Gemini API key:")
        print("   cp .env.example .env")
        print("   # Edit .env and add your GEMINI_API_KEY")
        
        print("\n2. Setup YouTube API credentials:")
        setup_oauth_credentials()
        
        print("\n3. Install dependencies:")
        print("   pip install -r requirements.txt")
        
        print("\n4. Install ffmpeg (required for video processing):")
        print("   Mac: brew install ffmpeg")
        print("   Linux: sudo apt-get install ffmpeg")
        print("   Windows: Download from ffmpeg.org")
        
        print("\n5. Run test:")
        print("   python main.py test")
        
        print("\n✅ After setup, run: python main.py schedule")
        return
    
    # Check setup for other commands
    if args.command != "test":
        if not automation.check_setup():
            print("\nRun 'python main.py setup' for help")
            return
    
    # Execute commands
    try:
        if args.command == "download":
            automation.download_trending(args.query, args.max)
        
        elif args.command == "analyze":
            if not args.video:
                print("❌ Please provide --video path")
                return
            automation.analyze_video(args.video)
        
        elif args.command == "create":
            if not args.video:
                print("❌ Please provide --video path")
                return
            analysis = automation.analyze_video(args.video)
            automation.create_reels(args.video, analysis)
        
        elif args.command == "upload":
            if not args.video:
                print("❌ Please provide --video path")
                return
            # Create dummy analysis for upload
            analysis = {
                "suggested_titles": ["Amazing Video"],
                "suggested_description": "Check this out!",
                "tags": ["#shorts", "#viral"],
                "hot_words": ["trending", "viral"],
                "main_topic": "Entertainment"
            }
            automation.upload_to_youtube(args.video, analysis, args.privacy)
        
        elif args.command == "run":
            automation.process_local_videos(upload=True, privacy=args.privacy)
        
        elif args.command == "schedule":
            automation.start_scheduler(args.time)
        
        elif args.command == "test":
            print("\n🧪 Running component tests...")
            print(f"✓ Config loaded")
            print(f"✓ VideoAnalyzer initialized")
            print(f"✓ VideoEditor initialized")
            print(f"✓ VideoDownloader initialized")
            print(f"✓ AutomationScheduler initialized")
            print("\n✅ All components loaded successfully!")
            print(f"   Source folder: {VIDEO_SOURCE_FOLDER}")
            print(f"   Output folder: {OUTPUT_FOLDER}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
