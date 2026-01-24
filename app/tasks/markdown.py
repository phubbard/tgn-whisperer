"""Prefect tasks for generating episode markdown."""
import json
from collections import defaultdict
from pathlib import Path
from prefect import task
from loguru import logger as log

from constants import SPEAKER_MAPFILE


@task(
    name="generate-episode-markdown",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def generate_episode_markdown(
    episode_dir: Path,
    episode_data: dict,
    speaker_map_path: Path,
    synopsis_path: Path
) -> Path:
    """
    Generate episode markdown file from transcript and attribution.

    Args:
        episode_dir: Episode directory path
        episode_data: Episode metadata dictionary (from RSS)
        speaker_map_path: Path to speaker map JSON
        synopsis_path: Path to synopsis text file

    Returns:
        Path to generated markdown file
    """
    md_path = episode_dir / "episode.md"

    if md_path.exists():
        log.info(f"Markdown already exists: {md_path}")
        return md_path

    log.info(f"Generating markdown for episode {episode_data.get('number')}")

    # Load speaker map and synopsis
    speaker_map = defaultdict(lambda: "Unknown")
    speaker_map.update(json.loads(speaker_map_path.read_text()))
    synopsis = synopsis_path.read_text()

    # Load chunked transcript
    whisper_output_path = episode_dir / "whisper-output.json"
    chunks = json.loads(whisper_output_path.read_text())
    log.debug(f"Loaded {len(chunks)} transcript chunks")

    # Map speaker IDs to names
    attributed_chunks = []
    for start_time, speaker_id, text in chunks:
        speaker_name = speaker_map[speaker_id]
        attributed_chunks.append((start_time, speaker_name, text))

    # Generate markdown header
    title = episode_data.get('title', 'Unknown Episode')
    pub_date = episode_data.get('pub_date', 'Unknown date')
    subtitle = episode_data.get('subtitle', '')
    episode_url = episode_data.get('episode_url', '')
    mp3_url = episode_data.get('mp3_url', '')

    md_content = f'''---
search:
  exclude: true
---

# {title}
Published on {pub_date}

{subtitle}

## Synopsis
{synopsis}

## Links
- [episode page]({episode_url})
- [episode MP3]({mp3_url})
- [episode webpage snapshot](episode.html)
- [episode MP3 - local mirror](episode.mp3)

## Transcript
'''

    # Generate transcript table
    table_header = '|*Speaker*||\n|----|----|\n'
    table_rows = []
    for _, speaker, text in attributed_chunks:
        # Escape pipe characters in text
        escaped_text = text.replace('|', '\\|')
        table_rows.append(f"|{speaker}|{escaped_text}|\n")

    md_content += table_header + ''.join(table_rows)

    # Write markdown file
    md_path.write_text(md_content)
    log.success(f"Generated markdown: {md_path} ({len(md_content)} characters)")

    return md_path


@task(
    name="copy-episode-files",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def copy_episode_files(episode_dir: Path, site_dir: Path) -> bool:
    """
    Copy episode files to site directory.

    Args:
        episode_dir: Source episode directory
        site_dir: Destination site directory

    Returns:
        True if files were copied successfully
    """
    import shutil

    files_to_copy = [
        'episode.md',
        'episode.mp3',
        'episode.html'
    ]

    copied_count = 0
    for filename in files_to_copy:
        src = episode_dir / filename
        dst = site_dir / filename

        if not src.exists():
            log.debug(f"Source file doesn't exist, skipping: {filename}")
            continue

        # Only copy if destination doesn't exist or source is newer
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            log.info(f"Copying {filename} to {site_dir}")
            shutil.copy2(src, dst)
            copied_count += 1
        else:
            log.debug(f"File up to date, skipping: {filename}")

    log.success(f"Copied {copied_count} files to site directory")
    return True
