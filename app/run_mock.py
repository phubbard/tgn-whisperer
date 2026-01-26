#!/usr/bin/env python3
"""Run the podcast workflow against mock servers.

Usage:
    uv run python app/run_mock.py

This script:
1. Cleans up any previous mock run data
2. Starts a mock server in a background thread
3. Runs the Prefect workflow against it
4. Shuts down the mock server when done

Output directories: podcasts/mock/ and sites/mock/
Cleanup: rm -rf podcasts/mock sites/mock
"""

import os
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Configure mock environment - MUST be set before imports
os.environ.setdefault("TRANSCRIPTION_API_BASE_URL", "http://localhost:5099")

# Fast failure for mock testing (don't wait 5 minutes between retries)
os.environ.setdefault("TRANSCRIBE_RETRIES", "1")
os.environ.setdefault("TRANSCRIBE_RETRY_DELAY", "5")

# Deploy to local directory instead of /usr/local/www
_base_dir = Path(__file__).parent.parent
os.environ.setdefault("DEPLOY_BASE_PATH", str(_base_dir / "deployed"))

# Ensure app directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flows.podcast import process_podcast
from models.podcast import Podcast
from mock_server import app as mock_app

# Define mock podcast locally - not in shared models, so production never sees it
MOCK_PODCAST = Podcast(
    name="mock",
    rss_url="http://localhost:5099/rss/mock.xml",
    emails=[],  # No email notifications for mock runs
    doc_base_url="http://localhost:5099",
)


def run_mock_server():
    """Run the mock server in a background thread."""
    # Disable Flask's reloader and debugger for background thread
    mock_app.run(host="localhost", port=5099, debug=False, use_reloader=False)


def cleanup_mock_data():
    """Clean up previous mock run data to ensure fresh state."""
    base_dir = Path(__file__).parent.parent

    # Clean mock directories
    for dir_name in ["podcasts/mock", "sites/mock", "deployed/mock"]:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            print(f"Cleaning up {dir_path}")
            shutil.rmtree(dir_path)

    # Ensure deployed directory exists
    deployed_dir = base_dir / "deployed"
    deployed_dir.mkdir(exist_ok=True)

    # Clean mock notification file
    notified_file = base_dir / "mock-notified.json"
    if notified_file.exists():
        notified_file.unlink()

    # Clear Prefect's result cache to avoid stale cached results
    prefect_storage = Path.home() / ".prefect" / "storage"
    if prefect_storage.exists():
        print(f"Clearing Prefect cache at {prefect_storage}")
        shutil.rmtree(prefect_storage)


def create_mock_site_config():
    """Create the mock site configuration files needed for zensical build."""
    base_dir = Path(__file__).parent.parent
    site_dir = base_dir / "sites" / "mock"
    docs_dir = site_dir / "docs"

    # Create directories
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Create mkdocs.yml
    mkdocs_yml = site_dir / "mkdocs.yml"
    mkdocs_yml.write_text("""site_name: Mock Podcast
site_url: http://localhost:5099/
site_description: Mock podcast for testing the transcription workflow
site_author: Test
copyright: "&copy; 2025 Test"

theme:
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
  features:
    - navigation.instant
    - navigation.instant.progress
    - navigation.tabs
    - navigation.sections
    - navigation.path
    - toc.integrate

plugins: []

nav:
  - Home: index.md
  - Episodes: episodes.md
""")

    # Create index.md
    index_md = docs_dir / "index.md"
    index_md.write_text("""## Mock Podcast

This is a mock podcast site for testing the transcription workflow.

## Episodes

Click on [Episodes](episodes.md) to see the list of mock episodes.
""")

    # Create episodes.md with mock episode links
    # These match the episodes served by mock_server.py
    episodes_md = docs_dir / "episodes.md"
    ts = datetime.now().astimezone().isoformat()
    episodes_md.write_text(f"""### Page updated {ts} - 3 episodes
- [Mock Episode 3: The Latest One](3.0/episode.md) Mon, 20 Jan 2025 12:00:00 +0000
- [Mock Episode 2: The Middle One](2.0/episode.md) Mon, 13 Jan 2025 12:00:00 +0000
- [Mock Episode 1: The First One](1.0/episode.md) Mon, 06 Jan 2025 12:00:00 +0000
""")

    print(f"Created mock site config at {site_dir}")


if __name__ == "__main__":
    print("Cleaning up previous mock data...")
    cleanup_mock_data()

    print("Creating mock site config...")
    create_mock_site_config()

    print("Starting mock server...")
    server_thread = threading.Thread(target=run_mock_server, daemon=True)
    server_thread.start()

    # Give the server a moment to start
    time.sleep(1)

    print("Mock server running on http://localhost:5099")
    print("Running mock podcast workflow...")
    print()

    try:
        process_podcast(MOCK_PODCAST)
    finally:
        print("\nMock workflow complete. Server shutting down.")
