"""
Video Downloader Module - Downloads videos from various platforms
"""
import os
import re
from pathlib import Path
from typing import Optional, List
import yt_dlp
from config import VIDEO_SOURCE_FOLDER


class VideoDownloader:
    """Downloads videos from YouTube, TikTok, Instagram, etc."""
    
    def __init__(self):
        self.download_folder = VIDEO_SOURCE_FOLDER
        os.makedirs(self.download_folder, exist_ok=True)
    
    def _get_ydl_options(self, filename: Optional[str] = None) -> dict:
        """Get yt-dlp options for downloading"""
        outtmpl = filename if filename else "%(title)s_%(id)s.%(ext)s"
        output_path = os.path.join(self.download_folder, outtmpl)
        
        return {
            'format': 'best[height<=1080]',  # Best quality up to 1080p
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'extract_audio': False,
            'writethumbnail': True,
            'writeinfojson': True,
            'cookiesfrombrowser': None,  # Optional: ('chrome',) or ('firefox',)
        }
    
    def download_video(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Download video from URL
        
        Args:
            url: Video URL (YouTube, TikTok, Instagram, etc.)
            filename: Optional custom filename
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            print(f"Downloading: {url}")
            
            options = self._get_ydl_options(filename)
            
            with yt_dlp.YoutubeDL(options) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                
                # Download video
                ydl.download([url])
                
                # Find downloaded file
                title = info.get('title', 'unknown')
                video_id = info.get('id', '')
                ext = info.get('ext', 'mp4')
                
                expected_filename = f"{title}_{video_id}.{ext}"
                file_path = os.path.join(self.download_folder, expected_filename)
                
                if os.path.exists(file_path):
                    print(f"Downloaded to: {file_path}")
                    return file_path
                else:
                    # Try to find file with similar name
                    for f in os.listdir(self.download_folder):
                        if video_id in f and f.endswith(('.mp4', '.mkv', '.webm')):
                            return os.path.join(self.download_folder, f)
                
                return None
                
        except Exception as e:
            print(f"Download error: {e}")
            return None
    
    def download_playlist(self, playlist_url: str, max_videos: int = 5) -> List[str]:
        """
        Download videos from a playlist
        
        Args:
            playlist_url: Playlist URL
            max_videos: Maximum number of videos to download
            
        Returns:
            List of downloaded file paths
        """
        downloaded = []
        
        try:
            options = {
                **self._get_ydl_options(),
                'playlistend': max_videos,
            }
            
            with yt_dlp.YoutubeDL(options) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                if 'entries' not in playlist_info:
                    print("No videos found in playlist")
                    return []
                
                entries = list(playlist_info['entries'])[:max_videos]
                
                for entry in entries:
                    if entry:
                        video_url = entry.get('webpage_url') or entry.get('url')
                        if video_url:
                            file_path = self.download_video(video_url)
                            if file_path:
                                downloaded.append(file_path)
                
                return downloaded
                
        except Exception as e:
            print(f"Playlist download error: {e}")
            return []
    
    def search_and_download(self, query: str, max_results: int = 3, 
                           platform: str = "youtube") -> List[str]:
        """
        Search for videos and download them
        
        Args:
            query: Search query
            max_results: Number of videos to download
            platform: Platform to search (youtube, tiktok)
            
        Returns:
            List of downloaded file paths
        """
        try:
            if platform == "youtube":
                search_query = f"ytsearch{max_results}:{query}"
            elif platform == "tiktok":
                # TikTok search requires different approach
                print("TikTok search not directly supported. Please provide URLs.")
                return []
            else:
                search_query = f"ytsearch{max_results}:{query}"
            
            options = self._get_ydl_options()
            downloaded = []
            
            with yt_dlp.YoutubeDL(options) as ydl:
                search_results = ydl.extract_info(search_query, download=False)
                
                if 'entries' not in search_results:
                    return []
                
                for entry in search_results['entries'][:max_results]:
                    if entry:
                        video_url = entry.get('webpage_url')
                        if video_url:
                            file_path = self.download_video(video_url)
                            if file_path:
                                downloaded.append(file_path)
                
                return downloaded
                
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_trending_shorts(self, niche: str = "", max_results: int = 5) -> List[str]:
        """
        Download trending YouTube Shorts
        
        Note: Direct trending shorts download requires special handling
        """
        try:
            # Search for popular short-form content
            queries = [
                f"trending {niche} shorts" if niche else "trending shorts",
                f"viral {niche} tiktok" if niche else "viral tiktok",
                f"popular {niche} reels" if niche else "popular reels"
            ]
            
            downloaded = []
            for query in queries:
                results = self.search_and_download(query, max_results=2)
                downloaded.extend(results)
                if len(downloaded) >= max_results:
                    break
            
            return downloaded[:max_results]
            
        except Exception as e:
            print(f"Error getting trending: {e}")
            return []
    
    def list_downloaded_videos(self) -> List[str]:
        """List all downloaded videos in the source folder"""
        video_extensions = ('.mp4', '.mkv', '.webm', '.avi', '.mov')
        
        videos = []
        if os.path.exists(self.download_folder):
            for file in os.listdir(self.download_folder):
                if file.endswith(video_extensions):
                    videos.append(os.path.join(self.download_folder, file))
        
        return sorted(videos)
    
    def clean_old_downloads(self, keep_count: int = 20):
        """Remove old downloaded videos, keeping only the most recent"""
        try:
            videos = self.list_downloaded_videos()
            
            if len(videos) <= keep_count:
                return
            
            # Sort by modification time
            videos.sort(key=lambda x: os.path.getmtime(x))
            
            # Remove oldest videos
            to_remove = videos[:-keep_count]
            for video in to_remove:
                try:
                    os.remove(video)
                    # Also remove thumbnail and json if exist
                    base = video.rsplit('.', 1)[0]
                    for ext in ['.jpg', '.webp', '.json']:
                        extra_file = base + ext
                        if os.path.exists(extra_file):
                            os.remove(extra_file)
                    print(f"Removed old download: {video}")
                except Exception as e:
                    print(f"Error removing {video}: {e}")
                    
        except Exception as e:
            print(f"Error cleaning downloads: {e}")


if __name__ == "__main__":
    # Test downloader
    downloader = VideoDownloader()
    
    print("Video Downloader Test")
    print(f"Download folder: {downloader.download_folder}")
    
    # List existing videos
    existing = downloader.list_downloaded_videos()
    print(f"\nExisting videos: {len(existing)}")
    for v in existing[:5]:
        print(f"  - {os.path.basename(v)}")
