# YouTube channel setup & upload guide

## What the bot uploads vs what you set in YouTube Studio

| Item | Where you set it | Used by this project? |
|------|------------------|------------------------|
| **Channel name** | [YouTube Studio](https://studio.youtube.com) → Customization → Basic info | Shown **on the video slides** via `CHANNEL_NAME` in `.env` |
| **Channel bio / description** | Studio → Customization → Basic info | **You** write manually (not uploaded by script) |
| **Profile picture (logo)** | Studio → Customization → Branding | **You** upload in Studio; optional copy on slides via `assets/channel_logo.png` |
| **Banner** | Studio → Customization → Branding | **You** upload manually |
| **Video title, description, tags** | Generated per tip | **Yes** — on each upload |
| **Thumbnail** | Studio after upload, or API | Optional later — not auto-set yet |

You do **not** enter your channel URL into the code. When you sign in with OAuth, uploads go to **the Google account you authorize**.

---

## Step 1 — Brand your channel (one time)

1. Open [YouTube Studio](https://studio.youtube.com).
2. **Customization → Basic info**
   - Channel name: e.g. `Daily Productivity Tips`
   - Description: e.g. `Daily 30-second tips on AI, email, and focus. New Short every day.`
3. **Customization → Branding**
   - Upload **profile picture** (800×800 recommended).
   - Upload **banner** (2560×1440).
4. Match your `.env` so slides match the channel:

```env
CHANNEL_NAME=Daily Productivity Tips
CHANNEL_CTA=Follow for daily tips
TIP_BRAND_COLOR=#f97316
```

5. (Optional) Save your logo as `assets/channel_logo.png` (square PNG, ~500×500).

---

## Step 2 — Google Cloud & OAuth (one time)

1. [Google Cloud Console](https://console.cloud.google.com/) → create project.
2. Enable **YouTube Data API v3**.
3. **Credentials → OAuth client ID → Desktop app** → download JSON → save as `client_secrets.json` in the project root.
4. On your Mac:

```bash
cd /Users/apple/Desktop/AI-Automation
source venv/bin/activate
python main.py test
```

5. First upload opens a browser — sign in with the **same Google account as your YouTube channel**.
6. Token saves to `youtube_token.pickle` (keep private).

---

## Step 3 — Create an improved Short locally

```bash
pip install -r requirements.txt
python main.py daily-tip --no-upload
```

Watch: `output_reels/tips/tip_YYYY-MM-DD.mp4`

Optional background music: add royalty-free `assets/background_music.mp3` (low volume mixed automatically).

---

## Step 4 — Upload to your channel

**Private first (recommended):**

```bash
python main.py daily-tip --upload --privacy private
```

**When ready for everyone:**

```bash
python main.py daily-tip --upload --privacy public
```

**Upload an existing file:**

```bash
python main.py upload --video "./output_reels/tips/tip_2026-05-19.mp4" --privacy private
```

After upload, the terminal prints: `https://youtube.com/shorts/VIDEO_ID`

---

## Step 5 — GitHub Actions (daily auto-upload)

1. Repo → **Settings → Secrets**:
   - `GEMINI_API_KEY`
   - `YOUTUBE_CLIENT_SECRETS_JSON` — paste full `client_secrets.json` content
   - `YOUTUBE_TOKEN_PICKLE_B64` — from Mac:

```bash
base64 -i youtube_token.pickle | pbcopy
```

2. Run workflow: **Actions → Daily Tip Short (Idea 2) → Run workflow** → set `upload` = `true`.

---

## Sharing your channel URL

Your channel URL looks like:

- `https://www.youtube.com/@YourChannelHandle`
- or `https://www.youtube.com/channel/UCxxxxxxxx`

You **do not** paste this into the upload code. OAuth links the app to that channel automatically.

To align slide branding with your channel, only set `CHANNEL_NAME` and optional logo in `.env`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Upload goes to wrong account | Delete `youtube_token.pickle`, re-run upload, pick correct Google account |
| Quota / Gemini errors | Tips use built-in scripts; fix API key/billing for AI-written tips |
| No background music | Add `assets/background_music.mp3` (royalty-free) |
| Video too short | Increase `TIP_SECONDS_PER_SLIDE=7` in `.env` |
