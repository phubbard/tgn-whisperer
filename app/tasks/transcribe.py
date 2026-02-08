"""Prefect tasks for audio transcription via Fluid Audio API."""
import json
import os
import time
import requests
from pathlib import Path
from prefect import task
from prefect.cache_policies import INPUTS
from utils.logging import get_logger

from constants import TRANSCRIPTION_API_BASE_URL

log = get_logger()

# Configurable retry settings (shorter for mock/testing)
TRANSCRIBE_RETRIES = int(os.environ.get("TRANSCRIBE_RETRIES", "2"))
TRANSCRIBE_RETRY_DELAY = int(os.environ.get("TRANSCRIBE_RETRY_DELAY", "300"))

# Polling settings for async API
POLL_INTERVAL = int(os.environ.get("TRANSCRIBE_POLL_INTERVAL", "15"))
POLL_TIMEOUT = int(os.environ.get("TRANSCRIBE_POLL_TIMEOUT", "1800"))


@task(
    name="transcribe-audio",
    retries=TRANSCRIBE_RETRIES,
    retry_delay_seconds=TRANSCRIBE_RETRY_DELAY,
    cache_policy=INPUTS,
    timeout_seconds=1800,  # 30 minute timeout
    log_prints=True
)
def transcribe_audio(episode_dir: Path, podcast_name: str, episode_number: float, mp3_path: Path) -> Path:
    """
    Transcribe audio file using Fluid Audio API.

    Submits the audio file, then polls for the result.

    Args:
        episode_dir: Episode directory path
        podcast_name: Name of the podcast
        episode_number: Episode number
        mp3_path: Path to MP3 file to transcribe

    Returns:
        Path to transcription JSON file

    Raises:
        requests.HTTPError: If transcription API call fails
        TimeoutError: If polling exceeds POLL_TIMEOUT
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

    # Submit to Fluid Audio API (async - returns job ID immediately)
    submit_url = f"{TRANSCRIPTION_API_BASE_URL}/submit/{podcast_name}/{episode_number}"

    log.info(f"Submitting for transcription: {podcast_name} episode {episode_number}")
    log.info(f"API URL: {submit_url}")
    log.info(f"MP3: {mp3_path} ({mp3_path.stat().st_size / 1024 / 1024:.1f} MB)")

    with open(mp3_path, 'rb') as f:
        response = requests.post(submit_url, files={'file': f}, timeout=60)

    if response.status_code != 202:
        log.error(f"Submit failed: {response.status_code} {response.reason}")
        response.raise_for_status()

    job_data = response.json()
    job_id = job_data['jobId']
    log.info(f"Job submitted: {job_id}")

    # Poll for result
    result_url = f"{TRANSCRIPTION_API_BASE_URL}/result/{job_id}"
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > POLL_TIMEOUT:
            raise TimeoutError(f"Transcription polling timed out after {POLL_TIMEOUT}s for job {job_id}")

        time.sleep(POLL_INTERVAL)

        result = requests.get(result_url, timeout=30)

        if result.status_code == 200:
            # Transcription complete
            transcript_path.write_text(result.text)
            log.info(f"Transcription complete: {transcript_path} ({len(result.text)} bytes, {elapsed:.0f}s)")
            return transcript_path
        elif result.status_code == 202:
            log.debug(f"Job {job_id} still processing ({elapsed:.0f}s elapsed)")
        elif result.status_code == 404:
            raise RuntimeError(f"Job {job_id} not found")
        elif result.status_code == 500:
            raise RuntimeError(f"Transcription failed on server for job {job_id}")
        else:
            log.warning(f"Unexpected status {result.status_code} polling job {job_id}")
            result.raise_for_status()
