"""Prefect tasks for speaker attribution using Claude API."""
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from datetime import datetime

from anthropic import Anthropic
from prefect import task
from prefect.cache_policies import INPUTS
from utils.logging import get_logger
from tenacity import retry, stop_after_attempt

from constants import SPEAKER_MAPFILE, SYNOPSIS_FILE, CLAUDE_MODEL, CLAUDE_MAX_TOKENS


def _extract_between_tags(tag: str, string: str, strip: bool = False) -> list[str]:
    """Extract content between XML-style tags."""
    ext_list = re.findall(f"<{tag}>(.+?)</{tag}>", string, re.DOTALL)
    if strip:
        ext_list = [e.strip() for e in ext_list]
    return ext_list


ATTRIBUTION_PROMPT = '''
The following is a podcast transcript. Please write a two to four paragraph synopsis in a <synopsis> tag
and a JSON dictionary mapping speakers to their labels inside an <attribution> tag.
For example, {"SPEAKER_00": "Jason Heaton", "SPEAKER_01": "James"}.
If you can't guess the speakers' name, put "Unknown".
'''


@retry(stop=(stop_after_attempt(2)))
def _call_claude(client: Anthropic, text: str) -> tuple[dict, str]:
    """
    Call Claude API for speaker attribution and synopsis generation.

    Args:
        client: Anthropic API client
        text: Transcript text to process

    Returns:
        Tuple of (speaker_map dict, synopsis string)

    Raises:
        json.JSONDecodeError: If Claude response is not valid JSON
        IndexError: If attribution or synopsis tags are missing
    """
    message = client.messages.create(
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

    speaker_map = defaultdict(lambda: "Unknown")
    log.debug(f"Claude model: {message.model}")

    # Extract attribution JSON
    try:
        attribution_text = _extract_between_tags("attribution", message.content[0].text, strip=True)

        # Claude sometimes adds explanatory notes after the JSON, so extract just the JSON part
        json_str = attribution_text[0]
        start = json_str.find('{')
        if start == -1:
            raise ValueError("No JSON object found in attribution")

        # Find the matching closing brace
        brace_count = 0
        end = start
        for i in range(start, len(json_str)):
            if json_str[i] == '{':
                brace_count += 1
            elif json_str[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        # Extract and parse just the JSON part
        json_only = json_str[start:end]
        speaker_map.update(json.loads(json_only))
        log.debug(f"Speaker map: {dict(speaker_map)}")
    except json.JSONDecodeError as e:
        log.error(f"Error converting LLM output into valid JSON: {e}")
        log.error(f"Message content: {message.content}")
        log.error(f"Extracted text: {attribution_text}")
        raise e
    except (IndexError, ValueError) as e:
        log.error(f"Error extracting JSON from LLM output: {e}")
        log.error(f"Message text: {message.content[0].text}")
        raise e

    # Extract synopsis
    try:
        synopsis_text = _extract_between_tags("synopsis", message.content[0].text, strip=True)
        synopsis = synopsis_text[0]
        log.debug(f"Synopsis length: {len(synopsis)} characters")
    except IndexError as e:
        log.error(f"Error extracting synopsis from LLM output: {e}")
        log.error(f"Message text: {message.content[0].text}")
        raise e

    # Use defaultdict to fill in blanks with "Unknown"
    result = defaultdict(lambda: "Unknown")
    for k, v in speaker_map.items():
        result[k] = v

    return result, synopsis


def _process_transcription_chunks(transcript_data: dict) -> list[tuple]:
    """
    Process transcript segments into speaker-delimited chunks.

    Args:
        transcript_data: Transcription JSON data with segments

    Returns:
        List of tuples (start_time, speaker, text_chunk)
    """
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
        log.error(f"Claude API call failed: {e}")
        # Use default values on failure
        speaker_map = defaultdict(lambda: "Unknown")
        synopsis = "LLM attribution failed"

    # Save results
    speaker_map_path.write_text(json.dumps(dict(speaker_map)))
    synopsis_path.write_text(synopsis)

    log.info(f"Attribution saved: {speaker_map_path}")
    log.info(f"Synopsis saved: {synopsis_path}")

    return speaker_map_path, synopsis_path
