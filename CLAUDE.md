# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TGN Whisperer is an automated podcast transcription system that:
- Transcribes audio from podcast RSS feeds (The Grey NATO, 40 & 20, Hodinkee Radio)
- Uses Claude API for speaker attribution and synopsis generation
- Generates static documentation sites with searchable transcripts
- Runs on Raspberry Pi 4 with a Mac Studio backend (Fluid Audio) for transcription

Deployed sites: tgn.phfactor.net, wcl.phfactor.net, hodinkee.phfactor.net

## Development Workflow

**IMPORTANT**: This project uses a pull request workflow. All changes must be made via PRs:

1. **Create a feature branch** from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/description-of-change
   # or: fix/bug-description, docs/update-description, refactor/cleanup-description
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "Clear description of changes"
   ```

3. **Push branch and create PR**:
   ```bash
   git push -u origin feature/description-of-change
   # Then create PR via GitHub web UI or: gh pr create
   ```

4. **Wait for review and tests** - All PRs require:
   - Passing automated tests (GitHub Actions)
   - Code review and approval
   - Branch protection prevents direct pushes to `main`

See [PR_WORKFLOW.md](PR_WORKFLOW.md) for complete details on branch naming, review process, and best practices.

## Commands

```bash
# Install dependencies
uv sync

# Run full workflow (all 3 podcasts)
uv run python app/run_prefect.py

# Run individual podcasts
uv run python app/run_tgn.py
uv run python app/run_wcl.py
uv run python app/run_hodinkee.py

# Run tests
uv run pytest app/ -v

# Run single test file
uv run pytest app/test_rss_processing.py -v

# Reprocess specific episode
./reprocess tgn 14 --all --make          # Full reprocess
./reprocess wcl 100 --attribute --make   # Just re-attribute speakers
./reprocess tgn 361 --all --dry-run      # Preview without executing
```

## Running Tasks

**Always use the existing Prefect tasks and flows** when executing operations, rather than writing ad-hoc scripts or shell commands. The Prefect code handles retries, logging, caching, and error reporting.

Examples of running operations through Prefect code:

```python
# Rebuild episodes.md + build + deploy for a single podcast
from models.podcast import get_all_podcasts
from tasks.rss import fetch_rss_feed, process_rss_feed
from tasks.build import update_episodes_index
from flows.podcast import generate_and_deploy_site

podcasts = get_all_podcasts()
tgn = [p for p in podcasts if p.name == 'tgn'][0]

rss_content = fetch_rss_feed(tgn)
feed_data = process_rss_feed(rss_content, tgn.name)
update_episodes_index(tgn.name, feed_data['episodes'])
generate_and_deploy_site(tgn)
```

Key Prefect tasks available:
- `fetch_rss_feed(podcast)` → RSS content string
- `process_rss_feed(rss_content, podcast_name)` → dict with `episodes`, `total_count`, `modified_count`
- `update_episodes_index(podcast_name, episodes)` → rebuilds `sites/{podcast}/docs/episodes.md`
- `build_site(podcast_name)` → runs zensical, returns site path
- `generate_search_index(site_path)` → runs pagefind
- `deploy_site(podcast_name, site_path)` → rsyncs to `/usr/local/www/{podcast}`
- `generate_and_deploy_site(podcast)` → flow that runs shownotes + build + search + deploy

## Architecture

### Prefect Flow Hierarchy

Three-level orchestration using Prefect 3.6:

1. **Main Flow** (`app/flows/main.py`) - Entry point, processes all podcasts sequentially
2. **Podcast Flow** (`app/flows/podcast.py`) - Per-podcast: fetch RSS → process episodes → build site
3. **Episode Flow** (`app/flows/episode.py`) - Per-episode: download → transcribe → attribute → markdown

### Task Modules (`app/tasks/`)

- `rss.py` - RSS fetching and episode number processing
- `download.py` - MP3 and HTML downloads
- `transcribe.py` - Fluid Audio async API: submit + poll (see `openapi.yaml`)
- `attribute.py` - Claude API speaker attribution and synopsis
- `markdown.py` - Episode markdown generation
- `shownotes.py` - Podcast-specific shownotes generation
- `build.py` - Site building with zensical and pagefind
- `completion.py` - Episode completion checking
- `notifications.py` - Email notifications

### Key Data Models

- `app/models/podcast.py` - Podcast configuration (name, RSS URL, emails)
- `app/models/episode.py` - Episode dataclass (number, title, mp3_url, directory)

### Directory Structure

```
podcasts/{podcast}/{episode}/    # Working directory (downloads, transcripts)
sites/{podcast}/docs/{episode}/  # Publication directory (markdown for site)
```

### External Services

- **Fluid Audio** - Transcription API at stt.phfactor.net (Caddy proxy → axiom.phfactor.net:5051)
- **Anthropic Claude** - Speaker attribution via API (uses ANTHROPIC_API_KEY env var)
- **FastMail SMTP** - Email notifications (uses FASTMAIL_PASSWORD env var)

## Key Processing Details

### RSS Episode Numbering

`app/rss_processor.py` processes podcast RSS feeds to ensure all episodes have correct `itunes:episode` tags.

- **WCL and Hodinkee**: Generic gap-filling — fills missing `itunes:episode` tags chronologically, trusting existing tags.
- **TGN**: Title-based numbering — ignores all existing `itunes:episode` tags (Buzzsprout assigns wrong sequential numbers 1–373) and extracts real episode numbers from titles.

When `podcast_name='tgn'` is passed to `process_feed()`, it calls `extract_tgn_episode_number()` to parse titles, then assigns fractional numbers to unnumbered episodes.

#### TGN (The Grey NATO) - Title-Based Numbering

**Why**: Buzzsprout assigns sequential `itunes:episode` tags (1, 2, 3, ..., 373) that don't match TGN's actual numbering. The real episode numbers are hand-authored in episode titles.

**Title Parser** (`extract_tgn_episode_number()` in `rss_processor.py`):

| Format | Example | Extracts |
|--------|---------|----------|
| Modern em-dash | `The Grey NATO – 363 – Title` | 363 |
| Modern trailing | `The Grey NATO – 300!` | 300 |
| Ep/EP prefix | `The Grey Nato - EP 14 - "TGN Summit"` | 14 |
| Episode prefix | `The Grey Nato - Episode 01 - "All Lux'd Out"` | 1 |
| Number only | `The Grey Nato - 02 - Origin Stories` | 2 |
| Re-Reupload | `The Grey NATO – 206 Re-Reupload – ...` | None (→ 206.5) |
| Unnumbered | `TGN Chats - Chase Fancher`, `Out Of Office`, `Depth Charge` | None (→ fractional) |

**Fractional Episode Assignment** (for unnumbered episodes):
- Looks at previous and next numbered episodes in chronological order
- If gap exists between them: fills with next integer (e.g., 2 and 4 → 3)
- If no gap: uses fractional (e.g., 14 and 15 → 14.5)

**All 10 Known Fractional Episodes:**

| Number | Title |
|--------|-------|
| 14.5 | TGN Chats - Chase Fancher :: Oak & Oscar |
| 16.5 | TGN Chats - Merlin Schwertner (Nomos) And Jason Gallop (Roldorf) |
| 20.5 | The Grey Nato - Question & Answer #1 |
| 143.5 | Depth Charge - The Original Soundtrack by Oran Chan |
| 160.5 | The Grey NATO – A Week Off (And A Request!) |
| 206.5 | The Grey NATO – 206 Re-Reupload – New Watches! |
| 214.5 | Drafting High-End Watches – A TGN Special With Collective Horology |
| 260.5 | Drafting Our Favorite Watches Of The 1970s – A TGN Special |
| 282.5 | The Grey NATO – The Ineos Grenadier Minisode With Thomas Holland |
| 295.5 | Out Of Office – Back August 22nd |

**Directory Naming** (`format_episode_number()` in `constants.py`):
- Integer episodes: No .0 suffix (e.g., `363/`, not `363.0/`)
- Fractional episodes: Include decimal (e.g., `14.5/`, `295.5/`)

### Speaker Attribution

`app/tasks/attribute.py` sends diarized transcript to Claude, which returns:
- `<attribution>` JSON block mapping speaker IDs to names
- `<synopsis>` text block with episode summary

**Important**: Attribution uses regular `client.messages.create` with XML tag parsing — NOT the structured output beta (`client.beta.messages.parse`). The structured output approach was tried and failed: it returns empty `speaker_map` dicts while correctly generating synopses.

### Shownotes Generation

**CRITICAL: Shownotes data is expensive and must NEVER be re-fetched from scratch.**

The TGN shownotes scraper takes 1-2 hours to scrape all ~365 Substack episode pages. Results are stored in a **permanent append-only cache** at `app/data/tgn_related.jsonl` (~2.4MB). This file must never be deleted or regenerated — only new episodes are appended incrementally.

- **TGN**: Scrapes Substack pages for related links (`app/related_links_collector/`)
  - Cache: `app/data/tgn_related.jsonl` (PERMANENT, append-only — never delete!)
  - Working file: `app/data/tgn_urls.txt` (regenerated each run from RSS)
  - Error log: `app/data/tgn_exceptions.jsonl`
  - Output: `sites/tgn/docs/shownotes.md`
- **WCL**: Extracts links from RSS HTML (`app/tasks/shownotes.py`)
- **Hodinkee**: Placeholder (not implemented)

### Bit.ly Resolution

TGN historical episodes used bit.ly shortlinks. `bitly.json` contains manual mappings to avoid rate limits during scraping.

## Testing

Tests are in `app/test_*.py`. Pytest is configured to use `app/` as both pythonpath and testpaths (see `pyproject.toml`).

## Prefect Server

```bash
# Service management
sudo systemctl start/stop/restart prefect-server
sudo systemctl status prefect-server

# View logs
sudo journalctl -u prefect-server -f

# Web UI at http://webserver.phfactor.net:4200 (LAN-only) or http://localhost:4200
```

### Webhooks and Automations

Prefect automations are configured to send notifications via webhooks:
- **ntfy.sh** - Phone notifications on flow failures
- **Slack** - Messages on flow events and completions

**Service configuration:** `/etc/systemd/system/prefect-server.service`
Includes HTTP timeout settings to prevent ReadError issues:
```ini
Environment="PREFECT_API_REQUEST_TIMEOUT=30.0"
Environment="HTTPX_TIMEOUT=30.0"
```

See [WEBHOOK_FIX.md](WEBHOOK_FIX.md) for troubleshooting webhook issues.

## Operational Notes

### Running Scripts from the Correct Directory

Scripts in `app/` need `app/` on the Python path. Either run from the `app/` directory or use the `run_*.py` scripts in the project root. Running Prefect tasks directly from the project root will fail with `ModuleNotFoundError`.

### Site Build Timing on Raspberry Pi

The Pi is slow for site builds:
- zensical: ~4 min (TGN), ~7 min (WCL), ~3 min (Hodinkee)
- pagefind: ~10-22 seconds
- rsync deploy: ~3 minutes
- Total per site: ~8-12 minutes

### Podcast Flow Always Rebuilds

The podcast flow (`app/flows/podcast.py`) always runs `update_episodes_index()` and `generate_and_deploy_site()`, even when no new episodes are found. This ensures shownotes and episodes.md stay current with the RSS feed.

### Data Files That Must Be Preserved

These files are expensive to regenerate and should be treated as append-only:
- `app/data/tgn_related.jsonl` — TGN shownotes scrape cache (1-2 hours to rebuild)
- `app/data/bitly.json` — Manual bit.ly → canonical URL mappings
- `podcasts/{podcast}/{ep}/transcription.json` — Transcription results (~3.5 min each)
- `podcasts/{podcast}/{ep}/speaker-map.json` — Claude attribution results (API cost)
