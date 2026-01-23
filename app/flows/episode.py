"""Episode processing flow for individual episodes."""
from prefect import flow
from loguru import logger as log

from models.podcast import Podcast
from models.episode import Episode


@flow(name="process-episode", log_prints=True)
def process_episode(podcast: Podcast, episode_data: dict):
    """
    Process a single podcast episode.

    Workflow:
    1. Create episode object and directories
    2. Download MP3 file
    3. Transcribe audio (blocking call to Mac Studio on LAN)
    4. Download episode HTML page
    5. Attribute speakers using Claude
    6. Generate episode markdown

    Args:
        podcast: Podcast configuration object
        episode_data: Episode data from RSS feed

    Returns:
        Path to generated markdown file
    """
    log.info(f"Processing episode: {podcast.name} #{episode_data.get('number')}")

    # TODO: Create episode object and directories
    # episode = create_episode(episode_data)
    # create_episode_directory(episode)

    # TODO: Download MP3
    # mp3_path = download_mp3(episode)

    # TODO: Transcribe audio (blocking call to Mac Studio)
    # transcript = transcribe_audio(podcast.name, episode.number, mp3_path)
    # Note: transcribe_audio blocks for 30-90 minutes, which is fine
    # since it's a LAN call to Mac Studio with Fluid Audio

    # TODO: Download HTML in parallel with attribution
    # html_future = download_episode_html.submit(episode)
    # speaker_map = attribute_speakers(transcript, podcast.name)
    # html_path = html_future.result()

    # TODO: Generate final markdown
    # md_path = generate_episode_markdown(episode, transcript, speaker_map)

    log.info(f"Episode processing complete: {podcast.name} #{episode_data.get('number')}")
    return None
