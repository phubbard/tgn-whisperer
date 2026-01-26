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
from pathlib import Path

# Configure mock environment - MUST be set before imports
os.environ.setdefault("TRANSCRIPTION_API_BASE_URL", "http://localhost:5099")

# Fast failure for mock testing (don't wait 5 minutes between retries)
os.environ.setdefault("TRANSCRIBE_RETRIES", "1")
os.environ.setdefault("TRANSCRIBE_RETRY_DELAY", "5")

# Skip site build/deploy for mock (no zensical config)
os.environ.setdefault("SKIP_SITE_DEPLOY", "1")

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
    for dir_name in ["podcasts/mock", "sites/mock"]:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            print(f"Cleaning up {dir_path}")
            shutil.rmtree(dir_path)

    # Clean mock notification file
    notified_file = base_dir / "mock-notified.json"
    if notified_file.exists():
        notified_file.unlink()

    # Clear Prefect's result cache to avoid stale cached results
    prefect_storage = Path.home() / ".prefect" / "storage"
    if prefect_storage.exists():
        print(f"Clearing Prefect cache at {prefect_storage}")
        shutil.rmtree(prefect_storage)


if __name__ == "__main__":
    print("Cleaning up previous mock data...")
    cleanup_mock_data()

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
