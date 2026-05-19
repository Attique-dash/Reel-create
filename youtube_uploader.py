"""
YouTube Uploader Module
"""
import os
import sys
import pickle
import tempfile
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

TOKEN_FILE = "youtube_token.pickle"


class YouTubeUploader:
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self.authenticate()

    def authenticate(self):
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'rb') as token:
                    self.credentials = pickle.load(token)

            if not self.credentials or not self.credentials.valid:
                if (self.credentials and self.credentials.expired
                        and self.credentials.refresh_token):
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
                        print(f"ERROR: {YOUTUBE_CLIENT_SECRETS_FILE} not found!")
                        sys.exit(1)
                    flow = InstalledAppFlow.from_client_secrets_file(
                        YOUTUBE_CLIENT_SECRETS_FILE, [YOUTUBE_UPLOAD_SCOPE])
                    self.credentials = flow.run_local_server(port=0)

                fd, temp_path = tempfile.mkstemp(dir='.')
                try:
                    with os.fdopen(fd, 'wb') as tmp:
                        pickle.dump(self.credentials, tmp)
                    os.replace(temp_path, TOKEN_FILE)
                except Exception:
                    os.unlink(temp_path)
                    raise

            self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                                 credentials=self.credentials)
            print("✅ YouTube authenticated!")
        except Exception as e:
            print(f"Authentication error: {e}")
            raise

    def upload_video(self, video_path: str, title: str, description: str,
                     tags: list, category_id: int = 24,
                     privacy_status: str = "private") -> dict:
        try:
            if not os.path.exists(video_path):
                print(f"Error: Video not found: {video_path}")
                return None

            body = {
                "snippet": {"title": title, "description": description,
                            "tags": tags, "categoryId": category_id},
                "status": {"privacyStatus": privacy_status,
                           "selfDeclaredMadeForKids": False}
            }

            media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
            request = self.youtube.videos().insert(
                part=','.join(body.keys()), body=body, media_body=media)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Upload progress: {int(status.progress() * 100)}%")

            print(f"✅ Uploaded! ID: {response['id']}")
            print(f"   URL: https://youtube.com/shorts/{response['id']}")
            return response
        except HttpError as e:
            print(f"HTTP error: {e.resp.status} - {e.error_details}")
            return None
        except Exception as e:
            print(f"Upload error: {e}")
            return None

    def upload_short(self, video_path: str, analysis: dict,
                     privacy_status: str = "private") -> dict:
        try:
            titles = analysis.get("suggested_titles", [])
            title = titles[0] if titles else Path(video_path).stem
            if len(title) > 97:
                title = title[:97] + "..."
            if "#Shorts" not in title:
                title = f"{title} #Shorts"

            description = analysis.get("suggested_description", "")
            description += "\n\n#Shorts #YouTubeShorts #Viral"
            hot_words = analysis.get("hot_words", [])
            description += " " + " ".join(
                [f"#{w.replace(' ', '')}" for w in hot_words[:5]])

            tags = [t.lstrip('#') for t in analysis.get("tags", [])]
            tags.extend(hot_words)
            # Remove duplicates and enforce YouTube's 500 char total limit
            unique_tags = []
            seen = set()
            total_chars = 0
            for tag in tags:
                tag = tag.strip()
                if tag and tag.lower() not in seen:
                    # YouTube limits: 500 chars total, 30 chars per tag
                    if len(tag) <= 30 and total_chars + len(tag) + 1 <= 500:
                        unique_tags.append(tag)
                        seen.add(tag.lower())
                        total_chars += len(tag) + 1  # +1 for separator
            tags = unique_tags

            main_topic = analysis.get("main_topic", "Entertainment")
            category_id = VIDEO_CATEGORIES.get(main_topic, 24)

            return self.upload_video(video_path, title, description, tags,
                                     category_id, privacy_status)
        except Exception as e:
            print(f"Error uploading Short: {e}")
            return None


def setup_oauth_credentials():
    print("\n" + "=" * 60)
    print("YouTube OAuth2 Setup")
    print("=" * 60)
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create project → Enable YouTube Data API v3")
    print("3. Credentials → OAuth client ID → Desktop app")
    print("4. Download JSON → rename to client_secrets.json")
    print("=" * 60)