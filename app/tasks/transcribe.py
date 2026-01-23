"""Prefect tasks for audio transcription via Fluid Audio API."""
import json
import requests
from pathlib import Path
from prefect import task
from prefect.cache_policies import INPUTS
from loguru import logger as log


@task(
    name="transcribe-audio",
    retries=2,
    retry_delay_seconds=300,  # 5 minute retry delay for transcription failures
    cache_policy=INPUTS,
    timeout_seconds=7200,  # 2 hour timeout (transcription takes 30-90 minutes)
    log_prints=True
)
def transcribe_audio(episode_dir: Path, podcast_name: str, episode_number: float, mp3_path: Path) -> Path:
    """
    Transcribe audio file using Fluid Audio API.

    This makes a blocking POST request to the Fluid Audio server running on Mac Studio
    on the local network. The transcription typically takes 30-90 minutes per episode.

    Args:
        episode_dir: Episode directory path
        podcast_name: Name of the podcast
        episode_number: Episode number
        mp3_path: Path to MP3 file to transcribe

    Returns:
        Path to transcription JSON file

    Raises:
        requests.HTTPError: If transcription API call fails
    """
    transcript_path = episode_dir / "episode-transcribed.json"

    if transcript_path.exists():
        log.info(f"Transcript already exists: {transcript_path}")
        return transcript_path

    # Save whisperx.json metadata for compatibility with existing code
    whisperx_data = {
        'podcast': podcast_name,
        'episode': str(episode_number)
    }
    whisperx_path = episode_dir / "whisperx.json"
    whisperx_path.write_text(json.dumps(whisperx_data))
    log.debug(f"Wrote whisperx metadata: {whisperx_path}")

    # Call Fluid Audio API
    # Note: This is a BLOCKING call that takes 30-90 minutes
    # The API is running on Mac Studio (axiom.phfactor.net) on the local network
    api_url = f"http://axiom.phfactor.net:5051/submit/{podcast_name}/{episode_number}"

    log.info(f"Submitting for transcription: {podcast_name} episode {episode_number}")
    log.info(f"API URL: {api_url}")
    log.info(f"MP3: {mp3_path} ({mp3_path.stat().st_size / 1024 / 1024:.1f} MB)")
    log.warning("This will take 30-90 minutes - blocking call to Fluid Audio on Mac Studio")

    with open(mp3_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(api_url, files=files)

    if not response.ok:
        log.error(f"Transcription failed: {response.status_code} {response.reason}")
        response.raise_for_status()

    # Save transcription result
    transcript_path.write_text(response.text)
    log.success(f"Transcription complete: {transcript_path} ({len(response.text)} bytes)")

    return transcript_path
