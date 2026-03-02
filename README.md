# Faceless Social Media Scheduling Bot

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

Automate a faceless content channel across YouTube Shorts, TikTok, and Instagram/Facebook Reels. AI generates captions, schedules posts, and uploads videos automatically.

Perfect for content creators running faceless channels who want to scale posting without manual work.

---

## Features

- **AI Caption Generation** — Claude Sonnet 4 analyzes video filenames, searches the web for context, and writes platform-optimized captions with hashtags
- **Caption Refresh** — Generate unlimited fresh caption variations at 1/5 the cost to avoid repetition
- **YouTube Shorts Upload** — Fully automated via YouTube Data API v3 with scheduling and batch support
- **TikTok Upload** — Browser automation via Playwright with scheduling support
- **Meta (Instagram + Facebook) Upload** — Graph API integration for Reels (work in progress)
- **Smart Scheduling** — Per-platform posting times by day of week, configurable skip days
- **Rich Terminal UI** — Single control panel to manage everything
- **Batch Processing** — Upload in configurable batches to stay within platform quotas

---

## Project Structure

```
├── src/
│   ├── app.py                    # Main terminal UI control panel
│   ├── uploaders/
│   │   ├── youtube.py            # YouTube Data API v3 uploader
│   │   ├── tiktok.py             # TikTok Playwright browser automation
│   │   └── meta.py               # Meta Graph API (Instagram + Facebook)
│   └── captions/
│       ├── generator.py          # AI caption generation (Claude + web search)
│       └── refresher.py          # Caption variation generator
├── config/
│   ├── posting_schedule.json     # Day-of-week posting times per platform
│   ├── client_secret.json        # Google OAuth credentials (gitignored)
│   ├── youtube_token.pickle      # YouTube auth token (gitignored)
│   └── meta_config.json          # Meta API credentials (gitignored)
├── data/
│   └── captions.csv              # Content library (gitignored)
├── videos/                       # Upload-ready .mp4 files
├── docs/
│   ├── SETUP.md                  # YouTube API setup guide
│   ├── SCHEDULER_GUIDE.md        # Scheduling system docs
│   └── CONTRIBUTING.md           # Contribution guidelines
├── requirements.txt
└── README.md
```

---

## Platform Status

### YouTube Shorts — Fully Working

Uploads via the YouTube Data API v3 with OAuth authentication.

- Automated uploads with title, description, and hashtags from CSV
- Scheduled posting at optimal times per day of week
- Batch uploads (8-10 videos/day within API quota)
- Auto-retry on transient errors
- Progress tracking with upload summaries

### TikTok — Working (Browser Automation)

Uploads via Playwright controlling a real Chrome session.

- Automated video upload, caption entry, and hashtag insertion
- Scheduled posting via TikTok's date/time picker
- Connects to Chrome on debug port 9222 (requires manual login once)
- Batch upload support with progress tracking

### Meta (Instagram + Facebook Reels) — Work in Progress

The uploader code exists (`src/uploaders/meta.py`) using the Meta Graph API, but is not actively deployed yet. The integration covers:

- Instagram Reels via resumable upload (no public URL required)
- Facebook Reels via binary upload
- Scheduling support for both platforms

This will be activated once API credentials and testing are finalized.

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/faceless-social-bot.git
cd faceless-social-bot
pip3 install -r requirements.txt
```

For TikTok uploads, also install Playwright browsers:

```bash
playwright install chromium
```

### 2. Set Up API Keys

**Anthropic (required for caption generation):**

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

Add to `~/.zshrc` or `~/.bashrc` to persist across sessions.

**YouTube API (required for YouTube uploads):**

See [docs/SETUP.md](docs/SETUP.md) for full instructions. In short:

1. Create a project at [Google Cloud Console](https://console.cloud.google.com/)
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop app)
4. Download the JSON file to `config/client_secret.json`
5. Add yourself as a test user in the OAuth consent screen

### 3. Prepare Videos

Videos should follow this naming convention so the AI can generate accurate captions:

```
Subject_ContentType_YearEvent_Version.mp4
```

Examples:
- `LeBron_Dunk_2016Finals_V1.mp4`
- `Messi_FreeKick_2018WorldCup_V2.mp4`
- `Gordon_FlameSteak_2024HellsKitchen_V1.mp4`

The bot parses filenames to search for context and generate relevant captions, so descriptive names produce better results.

### 4. Run

```bash
python3 src/app.py
```

This opens the control panel where you can generate captions, upload to any platform, view the schedule, and manage settings.

---

## Workflow

### First Time Setup

1. **Generate captions** — The AI analyzes filenames, searches the web for context, and writes platform-specific captions. Results are saved to your CSV. Cost: ~$0.10/video.

2. **Review the CSV** — AI is accurate but not perfect. Open the CSV and tweak any captions or hashtags before uploading.

3. **Upload** — Choose a platform from the control panel. Videos are uploaded with captions and scheduled based on `config/posting_schedule.json`.

### Ongoing

- **Refresh captions** to get new variations at ~$0.02/video
- **Batch upload** to stay within daily quotas (YouTube: ~8-10/day)
- Videos can be reposted with fresh captions each week

---

## Scheduling

Posting times are configured per platform in `config/posting_schedule.json`:

```json
{
  "Monday":    { "tiktok": "19:00", "youtube": "14:00", "meta": "12:00" },
  "Tuesday":   { "tiktok": "19:00", "youtube": "15:00", "meta": "11:00" },
  "Wednesday": { "tiktok": "18:00", "youtube": "16:00", "meta": "12:00" },
  "Thursday":  { "tiktok": "08:00", "youtube": "14:00", "meta": "11:00" },
  "Friday":    { "tiktok": "17:00", "youtube": "16:00", "meta": "13:00" },
  "Saturday":  { "tiktok": "17:00", "youtube": "18:00", "meta": "10:00" }
}
```

Days not listed are skipped. Dates are calculated at runtime starting from the next day.

---

## Cost Breakdown

| Action | Cost per Video |
|--------|---------------|
| Caption generation (first time) | ~$0.10 |
| Caption refresh (variations) | ~$0.02 |
| YouTube upload | Free (API) |
| TikTok upload | Free (browser automation) |

For 75 videos: ~$8-10 initial generation, ~$1.50 per refresh cycle.

---

## Security

The following are **gitignored** and never committed:

- `config/client_secret*.json` — Google OAuth credentials
- `config/youtube_token.pickle` — YouTube auth token
- `config/meta_config.json` — Meta API access token and IDs
- `data/*.csv` — Generated caption data
- `videos/` — All video files
- `.env` — Environment variables

---

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
Set the environment variable: `export ANTHROPIC_API_KEY="sk-ant-your-key-here"`

**YouTube quota exceeded**
Use batch uploads (8-10 videos per day). Check quota at [Google Cloud Console](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas).

**TikTok login required**
Launch Chrome with remote debugging first, log in manually, then run the uploader:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

---

## Built With

- **Python 3.8+**
- **Anthropic Claude Sonnet 4** — AI caption generation with web search
- **YouTube Data API v3** — Video uploads and scheduling
- **Playwright** — Browser automation for TikTok
- **Meta Graph API** — Instagram and Facebook Reels (WIP)
- **Rich** — Terminal UI
- **OpenCV** — Video frame extraction

---

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
