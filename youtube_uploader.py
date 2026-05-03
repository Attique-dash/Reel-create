"""
YouTube Uploader Module - Handles OAuth2 and video uploads to YouTube
"""
import os
import sys
import json
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from config import (
    YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION, YOUTUBE_UPLOAD_SCOPE, VIDEO_CATEGORIES
)

# Token storage
TOKEN_FILE = "youtube_token.pickle"


class YouTubeUploader:
    """Handles YouTube authentication and video uploads"""
    
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with YouTube API using OAuth2"""
        try:
            # Load existing token
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # Refresh or create new credentials
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
                        print(f"ERROR: {YOUTUBE_CLIENT_SECRETS_FILE} not found!")
                        print("Please download your OAuth2 credentials from Google Cloud Console")
                        print("Visit: https://console.cloud.google.com/apis/credentials")
                        sys.exit(1)
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        YOUTUBE_CLIENT_SECRETS_FILE,
                        [YOUTUBE_UPLOAD_SCOPE]
                    )
                    self.credentials = flow.run_local_server(port=0)
                
                # Save token for future runs
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # Build YouTube service
            self.youtube = build(
                YOUTUBE_API_SERVICE_NAME,
                YOUTUBE_API_VERSION,
                credentials=self.credentials
            )
            
            print("Successfully authenticated with YouTube!")
            
        except Exception as e:
            print(f"Authentication error: {e}")
            raise
    
    def upload_video(self, video_path: str, title: str, description: str,
                     tags: list, category_id: int = 24, privacy_status: str = "private") -> dict:
        """
        Upload a video to YouTube
        
        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (default 24 = Entertainment)
            privacy_status: private, unlisted, or public
        """
        try:
            if not os.path.exists(video_path):
                print(f"Error: Video file not found: {video_path}")
                return None
            
            # Prepare video metadata
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": category_id
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }
            
            # Upload video
            print(f"Uploading: {title}")
            print(f"File: {video_path}")
            
            media = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True
            )
            
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Upload progress: {int(status.progress() * 100)}%")
            
            print(f"Upload complete! Video ID: {response['id']}")
            print(f"Video URL: https://youtube.com/shorts/{response['id']}")
            
            return response
            
        except HttpError as e:
            print(f"HTTP error occurred: {e.resp.status} - {e.error_details}")
            return None
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    def upload_short(self, video_path: str, analysis: dict, 
                     privacy_status: str = "private") -> dict:
        """
        Upload a YouTube Short with optimized metadata
        
        Args:
            video_path: Path to video file
            analysis: Video analysis data with titles, tags, etc.
            privacy_status: private, unlisted, or public
        """
        try:
            # Get title
            titles = analysis.get("suggested_titles", [])
            title = titles[0] if titles else Path(video_path).stem
            
            # Ensure title is optimized for Shorts
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Add Shorts indicator to title (optional)
            if "#Shorts" not in title:
                title = f"{title} #Shorts"
            
            # Get description
            description = analysis.get("suggested_description", "")
            description += "\n\n#Shorts #YouTubeShorts #Viral"
            
            # Add hot words as hashtags
            hot_words = analysis.get("hot_words", [])
            hashtags = " ".join([f"#{word.replace(' ', '')}" for word in hot_words[:5]])
            description += f"\n{hashtags}"
            
            # Get tags
            tags = analysis.get("tags", [])
            # Clean tags (remove # if present)
            tags = [tag.lstrip('#') for tag in tags]
            # Add hot words as tags
            tags.extend(hot_words)
            # Limit to 500 chars total for all tags
            tags = list(set(tags))[:15]  # Max 15 tags, unique
            
            # Determine category
            main_topic = analysis.get("main_topic", "Entertainment")
            category_id = VIDEO_CATEGORIES.get(main_topic, 24)
            
            # Upload
            return self.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                category_id=category_id,
                privacy_status=privacy_status
            )
            
        except Exception as e:
            print(f"Error uploading Short: {e}")
            return None
    
    def update_video_status(self, video_id: str, privacy_status: str) -> bool:
        """Update video privacy status (useful for scheduling public releases)"""
        try:
            body = {
                "id": video_id,
                "status": {
                    "privacyStatus": privacy_status
                }
            }
            
            self.youtube.videos().update(
                part="status",
                body=body
            ).execute()
            
            print(f"Updated video {video_id} to {privacy_status}")
            return True
            
        except Exception as e:
            print(f"Error updating video status: {e}")
            return False
    
    def get_channel_info(self) -> dict:
        """Get authenticated user's channel info"""
        try:
            response = self.youtube.channels().list(
                part="snippet,statistics",
                mine=True
            ).execute()
            
            if response.get("items"):
                channel = response["items"][0]
                return {
                    "id": channel["id"],
                    "title": channel["snippet"]["title"],
                    "description": channel["snippet"]["description"],
                    "subscribers": channel["statistics"].get("subscriberCount", 0),
                    "videos": channel["statistics"].get("videoCount", 0),
                    "views": channel["statistics"].get("viewCount", 0)
                }
            return None
            
        except Exception as e:
            print(f"Error getting channel info: {e}")
            return None
    
    def list_uploads(self, max_results: int = 10) -> list:
        """List recent uploads"""
        try:
            # Get upload playlist ID
            channels_response = self.youtube.channels().list(
                part="contentDetails",
                mine=True
            ).execute()
            
            if not channels_response.get("items"):
                return []
            
            uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get videos from uploads playlist
            playlist_response = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=max_results
            ).execute()
            
            videos = []
            for item in playlist_response.get("items", []):
                videos.append({
                    "id": item["snippet"]["resourceId"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published": item["snippet"]["publishedAt"]
                })
            
            return videos
            
        except Exception as e:
            print(f"Error listing uploads: {e}")
            return []


def setup_oauth_credentials():
    """
    Guide user through OAuth setup
    """
    print("=" * 60)
    print("YouTube API OAuth2 Setup Guide")
    print("=" * 60)
    print("\n1. Go to https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable the YouTube Data API v3:")
    print("   - Go to 'APIs & Services' > 'Library'")
    print("   - Search for 'YouTube Data API v3'")
    print("   - Click 'Enable'")
    print("4. Create OAuth2 credentials:")
    print("   - Go to 'APIs & Services' > 'Credentials'")
    print("   - Click 'Create Credentials' > 'OAuth client ID'")
    print("   - Application type: 'Desktop app'")
    print("   - Name: 'YouTube Automation'")
    print("   - Click 'Create'")
    print("5. Download the JSON file")
    print(f"6. Rename it to '{YOUTUBE_CLIENT_SECRETS_FILE}' and place in project folder")
    print("\nFor more help: https://developers.google.com/youtube/v3/getting-started")
    print("=" * 60)


if __name__ == "__main__":
    # Check if credentials file exists
    if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
        setup_oauth_credentials()
        sys.exit(1)
    
    # Test authentication
    uploader = YouTubeUploader()
    
    # Get channel info
    channel = uploader.get_channel_info()
    if channel:
        print(f"\nConnected to channel: {channel['title']}")
        print(f"Subscribers: {channel['subscribers']}")
        print(f"Total videos: {channel['videos']}")
        print(f"Total views: {channel['views']}")
