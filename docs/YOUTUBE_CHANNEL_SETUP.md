# YouTube channel setup & upload guide

## What the bot uploads vs what you set in YouTube Studio

| Item | Where you set it | Used by this project? |
|------|------------------|------------------------|
| **Channel name** | [YouTube Studio](https://studio.youtube.com) → Customization → Basic info | Shown **on video slides** via `CHANNEL_NAME` in `.env` |
| **Channel bio / description** | Studio → Customization → Basic info | **You** write manually |
| **Profile picture (logo)** | Studio → Customization → Branding | Optional on slides: `assets/channel_logo.png` |
| **Video title, description, tags** | Generated per topic | **Yes** — on each upload |

OAuth uploads go to **the Google account you authorize** (no channel URL in code).

---

## Step 1 — Brand your channel (one time)

1. [YouTube Studio](https://studio.youtube.com) → Customization.
2. Set channel name, description, profile picture, banner.
3. Match `.env`:

```env
CHANNEL_NAME=Daily Productivity Tips
CHANNEL_CTA=Follow for daily tips
TIP_BRAND_COLOR=#f97316
```

---

## Step 2 — Google Cloud & OAuth (one time)

1. [Google Cloud Console](https://console.cloud.google.com/) → enable **YouTube Data API v3**.
2. OAuth client ID → **Desktop app** → save as `client_secrets.json`.
3. `python main.py test` then first upload to sign in → `youtube_token.pickle`.

---

## Step 3 — Create a Short locally

Edit `content/video_topics.txt`, then:

```bash
python main.py queue-video --no-upload
```

Output: `output_reels/queue/video_YYYY-MM-DD_*.mp4`

---

## Step 4 — Upload

```bash
python main.py queue-video --upload --privacy private
# or upload an existing file:
python main.py upload --video "./output_reels/queue/video_2026-05-19_2010_abc.mp4" --privacy private
```

---

## Step 5 — GitHub Actions (2 Shorts per day)

Workflow: **Actions → Content Queue Shorts**

Secrets: `GEMINI_API_KEY`, `YOUTUBE_CLIENT_SECRETS_JSON`, `YOUTUBE_TOKEN_PICKLE_B64`

```bash
base64 -i youtube_token.pickle | pbcopy
```

Runs at 09:00 and 21:00 UTC by default (12 hours apart).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Wrong YouTube account | Delete `youtube_token.pickle`, re-upload |
| Same topic repeated | Check `content/.content_queue_state.json` or `queue-status --reset-queue` |
| Gemini errors | Fallback script still runs; check API key |
