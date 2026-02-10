"""Prefect tasks for speaker attribution using Claude API."""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from anthropic import Anthropic
from prefect import task
from prefect.cache_policies import INPUTS
from utils.logging import get_logger
from tenacity import retry, stop_after_attempt

from constants import SPEAKER_MAPFILE, SYNOPSIS_FILE, CLAUDE_MODEL, CLAUDE_MAX_TOKENS


ATTRIBUTION_PROMPT = '''The following is a podcast transcript. Analyze it and return:

1. A JSON speaker attribution block wrapped in <attribution> tags, mapping each speaker ID to their name:
<attribution>
{"SPEAKER_00": "Name", "SPEAKER_01": "Name"}
</attribution>

2. A two to four paragraph synopsis wrapped in <synopsis> tags:
<synopsis>
Synopsis text here.
</synopsis>

If you can't determine a speaker's name, use "Unknown".
'''


log = get_logger()


@retry(stop=(stop_after_attempt(2)))
def _call_claude(client: Anthropic, text: str) -> tuple[dict, str]:
    """
    Call Claude API for speaker attribution and synopsis generation.

    Args:
        client: Anthropic API client
        text: Transcript text to process

    Returns:
        Tuple of (speaker_map dict, synopsis string)
    """
    log = get_logger()

    response = client.messages.create(
        max_tokens=CLAUDE_MAX_TOKENS,
        system=ATTRIBUTION_PROMPT,
        messages=[
            {
                "role": "user",
                "content": text,
            }
        ],
        model=CLAUDE_MODEL,
    )

    log.debug(f"Claude model: {response.model}")

    result_text = response.content[0].text

    # Parse speaker map from <attribution> tags
    attr_match = re.search(r'<attribution>\s*(\{.*?\})\s*</attribution>', result_text, re.DOTALL)
    speaker_map = {}
    if attr_match:
        try:
            speaker_map = json.loads(attr_match.group(1))
        except json.JSONDecodeError:
            for line in attr_match.group(1).split('\n'):
                m = re.search(r'"(SPEAKER_\d+)"\s*:\s*"([^"]+)"', line)
                if m:
                    speaker_map[m.group(1)] = m.group(2)

    # Parse synopsis from <synopsis> tags
    syn_match = re.search(r'<synopsis>\s*(.*?)\s*</synopsis>', result_text, re.DOTALL)
    synopsis = syn_match.group(1) if syn_match else "Synopsis not available."

    log.debug(f"Speaker map: {speaker_map}")
    log.debug(f"Synopsis length: {len(synopsis)} characters")

    # Use defaultdict to fill in blanks with "Unknown"
    speaker_result = defaultdict(lambda: "Unknown")
    for k, v in speaker_map.items():
        speaker_result[k] = v

    return speaker_result, synopsis


def _process_transcription_chunks(transcript_data: dict) -> list[tuple]:
    """
    Process transcript segments into speaker-delimited chunks.

    Args:
        transcript_data: Transcription JSON data with segments

    Returns:
        List of tuples (start_time, speaker, text_chunk)
    """
    log = get_logger()

    rc = []
    speaker = None
    text_chunk = ''
    start = None

    for chunk in transcript_data['segments']:
        if 'speaker' not in chunk:
            log.warning(f"No speaker in chunk, skipping")
            continue

        # Add space after punctuation
        punctuation = ['.', '?', '!']
        if chunk['text'] and chunk['text'][-1] in punctuation:
            chunk['text'] += ' '

        if speaker != chunk['speaker']:
            # Dump the buffered output
            if speaker:
                rc.append((start, speaker, text_chunk))

            speaker = chunk['speaker']
            text_chunk = chunk['text']
            start = chunk['start']
        else:
            text_chunk += chunk['text']

    # Append final chunk
    if speaker:
        rc.append((start, speaker, text_chunk))

    return rc


@task(
    name="attribute-speakers",
    retries=3,
    retry_delay_seconds=180,  # 3 minute delay for API rate limits
    cache_policy=INPUTS,
    log_prints=True
)
def attribute_speakers(episode_dir: Path, transcript_path: Path, podcast_name: str) -> tuple[Path, Path]:
    """
    Attribute speakers in transcript using Claude API.

    Args:
        episode_dir: Episode directory path
        transcript_path: Path to transcription JSON
        podcast_name: Name of the podcast

    Returns:
        Tuple of (speaker_map_path, synopsis_path)

    Raises:
        FileNotFoundError: If transcript file doesn't exist
        anthropic.RateLimitError: If Claude API rate limit is exceeded
    """
    log = get_logger()
    speaker_map_path = episode_dir / SPEAKER_MAPFILE
    synopsis_path = episode_dir / SYNOPSIS_FILE
    whisper_output_path = episode_dir / "whisper-output.json"

    # If outputs already exist, return them
    if speaker_map_path.exists() and synopsis_path.exists():
        log.info(f"Speaker attribution already exists: {speaker_map_path}")
        speaker_map = defaultdict(lambda: "Unknown")
        speaker_map.update(json.loads(speaker_map_path.read_text()))
        synopsis = synopsis_path.read_text()
        return speaker_map_path, synopsis_path

    # Load and process transcript
    log.info(f"Processing transcript: {transcript_path}")
    transcript_data = json.loads(transcript_path.read_text())

    # Process into speaker-delimited chunks
    chunks = _process_transcription_chunks(transcript_data)
    log.info(f"Processed {len(chunks)} speaker chunks")

    # Save whisper output for debugging/compatibility
    whisper_output_path.write_text(json.dumps(chunks))
    log.debug(f"Saved whisper output: {whisper_output_path}")

    # Call Claude for attribution
    log.info(f"Calling Claude API for speaker attribution ({podcast_name})")
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Convert chunks to text format for Claude
    text = json.dumps(chunks)
    log.info(f"Sending {len(text)} characters to Claude")

    try:
        speaker_map, synopsis = _call_claude(client, text)
        log.info(f"Attribution complete: {len(speaker_map)} speaker(s) identified")
    except Exception as e:
        log.error(f"ATTRIBUTION FAILED for {podcast_name} episode in {episode_dir}")
        log.error(f"Claude API error: {type(e).__name__}: {e}")
        log.error(f"Transcript length: {len(text)} characters")
        # Log full traceback for debugging
        import traceback
        log.error(f"Full traceback:\n{traceback.format_exc()}")
        # Use default values on failure
        speaker_map = defaultdict(lambda: "Unknown")
        synopsis = "LLM attribution failed"
        # Re-log with context after saving defaults
        log.error(f"Saved fallback attribution to {speaker_map_path} and {synopsis_path}")

    # Save results
    speaker_map_path.write_text(json.dumps(dict(speaker_map)))
    synopsis_path.write_text(synopsis)

    log.info(f"Attribution saved: {speaker_map_path}")
    log.info(f"Synopsis saved: {synopsis_path}")

    return speaker_map_path, synopsis_path
