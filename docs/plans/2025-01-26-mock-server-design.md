# Mock Server Design

## Overview

A mocked running mode for the Prefect podcast transcription workflow, allowing end-to-end testing without hitting real RSS feeds, downloading real MP3s, or calling the Fluid Audio transcription service.

## Components

### 1. Mock Server (`app/mock_server.py`)

Single Flask app serving all mock endpoints on port 5099:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rss/mock.xml` | GET | Mock RSS feed with 3 episodes |
| `/audio/<episode>.mp3` | GET | Tiny silent MP3 file |
| `/submit/mock/<episode>` | POST | Mock transcript JSON response |

### 2. Silent Audio File (`app/mock_data/silence.mp3`)

Pre-generated 2-second silent MP3 (~5KB). Valid audio file that won't cause issues if accidentally sent to real transcription service.

### 3. Mock Runner (`app/run_mock.py`)

Runner script that:
- Defines `MOCK_PODCAST` inline (not in shared models, so production never sees it)
- Sets `TRANSCRIPTION_API_BASE_URL=http://localhost:5099`
- Runs the standard `process_podcast_flow`

## Mock Data Format

### RSS Feed (`/rss/mock.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Mock Podcast</title>
    <itunes:author>Mock Host</itunes:author>

    <item>
      <title>Mock Episode 3: The Latest One</title>
      <itunes:episode>3</itunes:episode>
      <pubDate>Mon, 20 Jan 2025 12:00:00 +0000</pubDate>
      <enclosure url="http://localhost:5099/audio/3.mp3" type="audio/mpeg"/>
      <link>http://localhost:5099/episode/3</link>
    </item>

    <!-- Episodes 2 and 1 follow, oldest last -->
  </channel>
</rss>
```

### Transcript Response (`/submit/mock/<episode>`)

```json
{
  "segments": [
    {"speaker": "SPEAKER_00", "start": 0.0, "text": "Welcome to episode N of the Mock Podcast."},
    {"speaker": "SPEAKER_01", "start": 3.2, "text": "Lorem ipsum dolor sit amet..."},
    {"speaker": "SPEAKER_02", "start": 8.5, "text": "Sed do eiusmod tempor..."},
    {"speaker": "SPEAKER_00", "start": 14.1, "text": "Ut enim ad minim veniam..."},
    {"speaker": "SPEAKER_01", "start": 19.8, "text": "Duis aute irure dolor..."},
    {"speaker": "SPEAKER_02", "start": 25.3, "text": "Excepteur sint occaecat..."}
  ]
}
```

- 3 speakers: SPEAKER_00, SPEAKER_01, SPEAKER_02
- Text includes episode number for easy identification
- ~6-8 segments per episode

## Usage

### Ad-hoc Run

```bash
# Terminal 1: Start mock server
uv run python app/mock_server.py

# Terminal 2: Run workflow
uv run python app/run_mock.py
```

Flow appears in Prefect UI alongside production runs.

### Registered Deployment (Optional)

```bash
prefect deployment build app/run_mock.py:process_podcast_flow \
    --name mock-podcast \
    --work-queue default
```

Then trigger from Prefect UI when mock server is running.

## Output Directories

- `podcasts/mock/1/`, `podcasts/mock/2/`, `podcasts/mock/3/` - Working directories
- `sites/mock/docs/1/`, `sites/mock/docs/2/`, `sites/mock/docs/3/` - Publication directories

Cleanup: `rm -rf podcasts/mock sites/mock`

## Design Decisions

1. **Separate runner script** - Keeps mock infrastructure isolated from production code
2. **MOCK_PODCAST defined inline** - Production imports never see it
3. **Single Flask server** - Simple, one process to manage
4. **Tiny real MP3** - Valid audio file, won't break if sent to real service
5. **3 episodes with varied text** - Enough to test iteration, easy to identify which episode data you're viewing
