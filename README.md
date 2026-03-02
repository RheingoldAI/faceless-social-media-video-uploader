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

## Design Tradeoffs

Building automation across multiple platforms means navigating different constraints. Here are the key decisions and the reasoning behind them.

### API vs Browser Automation

YouTube offers a mature, well-documented Data API with OAuth support, quota management, and scheduled publishing built in. The right call is obvious: use the API.

TikTok is a different story. There is no public upload API available to individual creators — TikTok's Content Posting API is restricted to approved businesses and requires a lengthy review process. The only viable path for an individual creator is browser automation via Playwright. This introduces fragility (DOM changes can break selectors, date pickers are notoriously hard to automate) but it's the only option that actually works today. The tradeoff is: brittleness in exchange for functionality that simply doesn't exist through official channels.

Meta sits in between. Instagram and Facebook both offer Graph API endpoints for Reels publishing, but the documentation is fragmented and the approval process for permissions is non-trivial. We chose the API route here because it exists and is more reliable long-term than browser automation, even though the setup cost is higher.

**The principle: use the most stable integration available per platform, not a uniform approach across all of them.**

### Batch Sizing

YouTube's Data API enforces a quota of 10,000 units per day. Each video upload consumes approximately 1,600 units. That gives a hard ceiling of ~6 uploads per day, but in practice the quota accounting is slightly more generous, allowing 8-10 uploads reliably.

Batching at 8-10 videos per day isn't a preference — it's a platform constraint. The system is designed around it: the uploader asks which batch to run (1-10, 11-20, etc.), calculates scheduled dates for that batch window, and picks up cleanly where the previous batch left off. This makes multi-day upload campaigns predictable rather than error-prone.

### Content and Schedule Separation

The CSV stores only content: filenames, captions, and hashtags. The posting schedule (which day gets which time, per platform) lives in a separate `posting_schedule.json` config file. Dates are calculated at runtime.

This separation means:
- **Refreshing captions** doesn't require re-entering schedule preferences
- **Changing posting times** doesn't require regenerating captions
- **Adding a new platform** only needs a new key in the schedule config — the CSV doesn't change
- **Batch uploads across multiple days** stay consistent because dates are derived from the schedule, not hardcoded in content

### Two-Tier Caption Generation

Initial caption generation uses Claude Sonnet 4 with web search enabled. The model searches the internet for context about each video (who's in it, what event, what happened) and writes informed, engaging captions. This costs ~$0.10 per video.

Caption refresh skips the web search and asks the model to write variations of existing captions. This costs ~$0.02 per video — 5x cheaper.

The insight: the expensive part is research, not writing. Once the context is established, generating variations is cheap. This two-tier approach lets you repost the same videos weekly with fresh captions without re-incurring the research cost each time.

---

## Why Claude Sonnet 4

Caption generation is the core intelligence of this system, so the model choice matters.

**Why Claude over GPT-4 or open-source models:**

- **Tool use (web search)** — Claude Sonnet 4 supports native tool use, which means the model can autonomously search the web mid-generation. When it encounters a video filename like `Tiger_ChipIn_2005Masters_V1.mp4`, it doesn't just guess — it searches for "Tiger Woods chip in 2005 Masters" and writes captions grounded in real context. This is the difference between generic filler and captions that reference the actual moment, the score, the stakes.

- **Cost-performance sweet spot** — Claude Sonnet 4 sits between Haiku (fast/cheap but less capable) and Opus (most capable but expensive). For content generation with web search, Sonnet gives high-quality output at a price point that makes batch processing 75+ videos practical (~$8-10 total). Opus would triple the cost without meaningfully better captions. Haiku would save money but produce noticeably weaker copy.

- **Structured output reliability** — The caption generator needs the model to return consistently formatted responses (separate TikTok caption, TikTok hashtags, YouTube caption, YouTube hashtags, Meta caption, Meta hashtags). Claude Sonnet 4 follows these formatting instructions reliably across hundreds of sequential generations without drift or hallucinated formatting.

- **Tone control** — Faceless content captions need a specific voice: engaging, slightly provocative, emoji-forward for TikTok, cleaner for YouTube, hashtag-optimized for Instagram. Claude handles per-platform tone shifting well within a single prompt, so one API call generates all platform variants simultaneously.

**Why not a local model:** Running inference locally (Llama, Mistral, etc.) would eliminate API costs but lose web search capability entirely. Since the value of these captions comes from contextual accuracy — not just creative writing — losing web search would fundamentally degrade output quality.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Language** | Python 3.8+ | Dominant ecosystem for automation, API clients, and browser control. Every platform SDK and tool used here has first-class Python support. |
| **AI** | Anthropic Claude Sonnet 4 | Native tool use for web search during generation. Best cost/quality ratio for batch content creation. See [Why Claude Sonnet 4](#why-claude-sonnet-4). |
| **YouTube** | YouTube Data API v3 + Google OAuth | Official API with scheduling, quota management, and resumable uploads. Most reliable path. |
| **TikTok** | Playwright | No public upload API exists for individual creators. Playwright provides the most robust browser automation with auto-wait, network interception, and persistent contexts. Chosen over Selenium for its modern async architecture and built-in retry logic. |
| **Meta** | Meta Graph API + Resumable Upload | Official API for Instagram/Facebook Reels. Resumable upload flow eliminates the need for public video hosting. |
| **Scheduling** | JSON config + runtime calculation | Dates are derived, not stored. Keeps content and schedule decoupled. See [Content and Schedule Separation](#content-and-schedule-separation). |
| **UI** | Rich (Python) | Terminal UI with tables, progress bars, and styled output. No web server or frontend framework needed for what is fundamentally a CLI tool. |
| **Video Analysis** | OpenCV | Extracts frames from video files for analysis. Lightweight, well-maintained, no GPU required. |

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/RheingoldAI/faceless-social-media-video-uploader.git
cd faceless-social-media-video-uploader
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

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
