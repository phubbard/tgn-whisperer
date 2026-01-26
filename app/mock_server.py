#!/usr/bin/env python3
"""Mock server for testing the podcast transcription workflow.

Provides fake RSS feed, MP3 files, and transcription responses.

Usage:
    uv run python app/mock_server.py

Endpoints:
    GET  /rss/mock.xml         - Mock RSS feed with 3 episodes
    GET  /audio/<n>.mp3        - Silent MP3 file
    POST /submit/mock/<n>      - Mock transcript response
"""

from flask import Flask, Response, send_file
from pathlib import Path

app = Flask(__name__)

MOCK_DATA_DIR = Path(__file__).parent / "mock_data"
HOST = "localhost"
PORT = 5099


def generate_rss_feed() -> str:
    """Generate mock RSS feed with 3 episodes."""
    items = []
    for n in [3, 2, 1]:  # Newest first
        titles = {
            1: "The First One",
            2: "The Middle One",
            3: "The Latest One",
        }
        # Dates in descending order
        dates = {
            3: "Mon, 20 Jan 2025 12:00:00 +0000",
            2: "Mon, 13 Jan 2025 12:00:00 +0000",
            1: "Mon, 06 Jan 2025 12:00:00 +0000",
        }
        items.append(f"""    <item>
      <title>Mock Episode {n}: {titles[n]}</title>
      <itunes:episode>{n}</itunes:episode>
      <pubDate>{dates[n]}</pubDate>
      <enclosure url="http://{HOST}:{PORT}/audio/{n}.mp3" type="audio/mpeg" length="8000"/>
      <link>http://{HOST}:{PORT}/episode/{n}</link>
      <description>This is mock episode {n} for testing the transcription workflow.</description>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Mock Podcast</title>
    <description>A mock podcast for testing the transcription workflow.</description>
    <itunes:author>Mock Host</itunes:author>
    <language>en-us</language>
    <atom:link href="http://{HOST}:{PORT}/rss/mock.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""


def generate_transcript(episode_number: int) -> dict:
    """Generate mock transcript with 3 speakers and episode-specific text."""
    lorem_segments = [
        ("SPEAKER_00", "Welcome to episode {n} of the Mock Podcast. Today we have an exciting discussion."),
        ("SPEAKER_01", "Lorem ipsum dolor sit amet, consectetur adipiscing elit. This is episode {n}."),
        ("SPEAKER_02", "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."),
        ("SPEAKER_00", "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."),
        ("SPEAKER_01", "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum."),
        ("SPEAKER_02", "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia."),
        ("SPEAKER_00", "That wraps up episode {n}. Thanks for listening to the Mock Podcast!"),
    ]

    segments = []
    start_time = 0.0
    for speaker, text in lorem_segments:
        segments.append({
            "speaker": speaker,
            "start": round(start_time, 1),
            "text": text.format(n=episode_number),
        })
        start_time += 5.5  # Each segment ~5.5 seconds apart

    return {"segments": segments}


@app.route("/rss/mock.xml")
def rss_feed():
    """Return mock RSS feed."""
    return Response(generate_rss_feed(), mimetype="application/rss+xml")


@app.route("/audio/<int:episode>.mp3")
def audio_file(episode: int):
    """Return silent MP3 file."""
    mp3_path = MOCK_DATA_DIR / "silence.mp3"
    if not mp3_path.exists():
        return Response("MP3 file not found", status=404)
    return send_file(mp3_path, mimetype="audio/mpeg")


@app.route("/submit/mock/<episode>", methods=["POST"])
def transcribe(episode: str):
    """Return mock transcript response."""
    import json
    # Handle both "3" and "3.0" formats
    episode_num = int(float(episode))
    transcript = generate_transcript(episode_num)
    return Response(json.dumps(transcript), mimetype="application/json")


@app.route("/episode/<int:episode>")
def episode_page(episode: int):
    """Return mock episode HTML page (for shownotes scraping)."""
    html = f"""<!DOCTYPE html>
<html>
<head><title>Mock Episode {episode}</title></head>
<body>
<h1>Mock Episode {episode}</h1>
<p>This is the show notes page for mock episode {episode}.</p>
<ul>
  <li><a href="https://example.com/link1">Example Link 1</a></li>
  <li><a href="https://example.com/link2">Example Link 2</a></li>
</ul>
</body>
</html>"""
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    print(f"Starting mock server on http://{HOST}:{PORT}")
    print(f"RSS feed: http://{HOST}:{PORT}/rss/mock.xml")
    print(f"Transcription endpoint: POST http://{HOST}:{PORT}/submit/mock/<episode>")
    app.run(host=HOST, port=PORT, debug=True)
