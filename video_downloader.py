"""
Video Downloader Module - Downloads videos from various platforms
"""
import os
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
        outtmpl = filename if filename else "%(title)s_%(id)s.%(ext)s"
        output_path = os.path.join(self.download_folder, outtmpl)

        return {
            "format": "best[height<=1080]",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            # FIX: removed writethumbnail / writeinfojson — they clutter the folder
            # FIX: removed cookiesfrombrowser: None — caused yt-dlp warnings
        }

    def download_video(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        try:
            print(f"[Downloader] Downloading: {url}")
            options = self._get_ydl_options(filename)

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)

                # Determine the actual output path yt-dlp used
                ext = info.get("ext", "mp4")
                title = info.get("title", "unknown")
                video_id = info.get("id", "")
                expected = os.path.join(
                    self.download_folder, f"{title}_{video_id}.{ext}"
                )

                if os.path.exists(expected):
                    print(f"[Downloader] Saved → {expected}")
                    return expected

                # Fallback: find by video_id
                for f in os.listdir(self.download_folder):
                    if video_id in f and f.endswith((".mp4", ".mkv", ".webm")):
                        full = os.path.join(self.download_folder, f)
                        print(f"[Downloader] Found → {full}")
                        return full

                print("[Downloader] Could not locate downloaded file.")
                return None

        except Exception as e:
            print(f"[Downloader] Error: {e}")
            return None

    def download_playlist(self, playlist_url: str, max_videos: int = 5) -> List[str]:
        downloaded = []
        try:
            options = {**self._get_ydl_options(), "playlistend": max_videos}
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                if "entries" not in info:
                    return []
                for entry in list(info["entries"])[:max_videos]:
                    if entry:
                        url = entry.get("webpage_url") or entry.get("url")
                        if url:
                            path = self.download_video(url)
                            if path:
                                downloaded.append(path)
            return downloaded
        except Exception as e:
            print(f"[Downloader] Playlist error: {e}")
            return []

    def search_and_download(
        self, query: str, max_results: int = 3, platform: str = "youtube"
    ) -> List[str]:
        try:
            search_query = f"ytsearch{max_results}:{query}"
            options = self._get_ydl_options()
            downloaded = []

            with yt_dlp.YoutubeDL(options) as ydl:
                results = ydl.extract_info(search_query, download=False)
                if "entries" not in results:
                    return []
                for entry in results["entries"][:max_results]:
                    if entry:
                        url = entry.get("webpage_url")
                        if url:
                            path = self.download_video(url)
                            if path:
                                downloaded.append(path)

            return downloaded

        except Exception as e:
            print(f"[Downloader] Search error: {e}")
            return []

    def list_downloaded_videos(self) -> List[str]:
        video_extensions = (".mp4", ".mkv", ".webm", ".avi", ".mov")
        videos = []
        if os.path.exists(self.download_folder):
            for f in os.listdir(self.download_folder):
                if f.endswith(video_extensions):
                    videos.append(os.path.join(self.download_folder, f))
        return sorted(videos)

    def clean_old_downloads(self, keep_count: int = 20):
        try:
            videos = self.list_downloaded_videos()
            if len(videos) <= keep_count:
                return
            videos.sort(key=lambda x: os.path.getmtime(x))
            for video in videos[:-keep_count]:
                try:
                    os.remove(video)
                    print(f"[Downloader] Removed old file: {video}")
                except Exception as e:
                    print(f"[Downloader] Could not remove {video}: {e}")
        except Exception as e:
            print(f"[Downloader] Clean error: {e}")


if __name__ == "__main__":
    d = VideoDownloader()
    existing = d.list_downloaded_videos()
    print(f"Existing videos: {len(existing)}")
    for v in existing[:5]:
        print(f"  {os.path.basename(v)}")