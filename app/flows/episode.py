"""Episode processing flow for individual episodes."""
from pathlib import Path
from prefect import flow
from loguru import logger as log

from models.podcast import Podcast
from tasks.download import (
    create_episode_directories,
    download_mp3,
    download_episode_html
)
from tasks.transcribe import transcribe_audio
from tasks.attribute import attribute_speakers
from tasks.markdown import (
    generate_episode_markdown,
    copy_episode_files
)
from tasks.rss import parse_episode_data


@flow(
    name="process-episode",
    flow_run_name="{podcast.name}-ep-{episode_entry[itunes:episode]}",
    log_prints=True
)
def process_episode(podcast: Podcast, episode_entry: dict):
    """
    Process a single podcast episode.

    Workflow:
    1. Create episode directories
    2. Parse episode data from RSS entry
    3. Download MP3 file
    4. Transcribe audio (blocking call to Mac Studio on LAN) - ~90 seconds
    5. Download episode HTML page (in parallel with attribution)
    6. Attribute speakers using Claude
    7. Generate episode markdown
    8. Copy files to site directory

    Args:
        podcast: Podcast configuration object
        episode_entry: Episode RSS entry dictionary

    Returns:
        Path to generated markdown file
    """
    # Parse episode data from RSS entry
    episode_data = parse_episode_data(episode_entry)
    episode_number = episode_data['number']

    log.info(f"Processing episode: {podcast.name} #{episode_number}")

    # Step 1: Create directories
    episode_dir, site_dir = create_episode_directories(podcast.name, episode_number)

    # Step 2: Download MP3
    mp3_path = download_mp3(episode_dir, episode_data['mp3_url'])

    # Step 3: Transcribe audio (blocking call to Mac Studio)
    # Note: This blocks for ~90 seconds, which is fine since it's a LAN call
    transcript_path = transcribe_audio(episode_dir, podcast.name, episode_number, mp3_path)

    # Step 4: Download HTML in parallel with attribution
    html_future = download_episode_html.submit(episode_dir, episode_data['episode_url'])

    # Step 5: Attribute speakers using Claude
    speaker_map_path, synopsis_path = attribute_speakers(episode_dir, transcript_path, podcast.name)

    # Wait for HTML download to complete (best-effort, non-blocking)
    html_path = html_future.result()

    # Step 6: Generate markdown
    md_path = generate_episode_markdown(episode_dir, episode_data, speaker_map_path, synopsis_path)

    # Step 7: Copy files to site directory
    copy_episode_files(episode_dir, site_dir)

    log.success(f"Episode processing complete: {podcast.name} #{episode_number}")
    return md_path
