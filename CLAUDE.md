# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TGN Whisperer is an automated podcast transcription system that:
- Transcribes audio from podcast RSS feeds (The Grey NATO, 40 & 20, Hodinkee Radio)
- Uses Claude API for speaker attribution and synopsis generation
- Generates static documentation sites with searchable transcripts
- Runs on Raspberry Pi 4 with a Mac Studio backend (Fluid Audio) for transcription

Deployed sites: tgn.phfactor.net, wcl.phfactor.net, hodinkee.phfactor.net

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

## Architecture

### Prefect Flow Hierarchy

Three-level orchestration using Prefect 3.6:

1. **Main Flow** (`app/flows/main.py`) - Entry point, processes all podcasts sequentially
2. **Podcast Flow** (`app/flows/podcast.py`) - Per-podcast: fetch RSS → process episodes → build site
3. **Episode Flow** (`app/flows/episode.py`) - Per-episode: download → transcribe → attribute → markdown

### Task Modules (`app/tasks/`)

- `rss.py` - RSS fetching and episode number processing
- `download.py` - MP3 and HTML downloads
- `transcribe.py` - Fluid Audio API calls (speech-to-text + diarization)
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

- **Fluid Audio** - LAN backend at axiom.phfactor.net:5051 for transcription
- **Anthropic Claude** - Speaker attribution via API (uses ANTHROPIC_API_KEY env var)
- **FastMail SMTP** - Email notifications (uses FASTMAIL_PASSWORD env var)

## Key Processing Details

### RSS Episode Numbering

`app/rss_processor.py` fills missing `itunes:episode` tags chronologically. Many podcast feeds have incomplete episode numbers, so this processor ensures all episodes have numbers.

**Important: TGN Episode Number Offset**
- TGN has a 10-episode offset between `itunes:episode` numbers and episode titles
- Example: `itunes:episode` 371 = "The Grey NATO – 361" in title
- This is due to 10 early episodes (pre-RSS or deleted) that aren't in the feed
- Our system uses `itunes:episode` for directory/file naming (e.g., `sites/tgn/docs/371.0/`)
- When users refer to "episode 362", they mean itunes:episode #372

### Speaker Attribution

`app/tasks/attribute.py` sends diarized transcript to Claude Sonnet, which returns:
- `<attribution>` JSON block mapping speaker IDs to names
- `<synopsis>` text block with episode summary

### Shownotes Generation

- **TGN**: Scrapes Substack pages for related links (`app/related_links_collector/`)
- **WCL**: Extracts links from RSS HTML (`app/wcl_shownotes.py`)
- **Hodinkee**: Placeholder generation

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
