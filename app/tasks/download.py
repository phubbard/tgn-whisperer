"""Prefect tasks for downloading episode files."""
import json
from pathlib import Path
import subprocess
from prefect import task
from prefect.cache_policies import INPUTS
from utils.logging import get_logger

from constants import SITE_ROOT, format_episode_number


@task(
    name="create-episode-directories",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def create_episode_directories(podcast_name: str, episode_number: float) -> tuple[Path, Path]:
    """
    Create episode and site directories for an episode.

    Args:
        podcast_name: Name of the podcast
        episode_number: Episode number

    Returns:
        Tuple of (episode_directory, site_directory) Path objects
    """
    log = get_logger()
    log.info(f"Creating directories for {podcast_name} episode {episode_number}")

    # Episode directory: podcasts/tgn/14/ (no .0 for integers)
    ep_num_str = format_episode_number(episode_number)
    episode_dir = Path('podcasts', podcast_name, ep_num_str).absolute()
    if not episode_dir.exists():
        log.info(f"Creating episode directory: {episode_dir}")
        episode_dir.mkdir(parents=True, exist_ok=True)
    else:
        log.debug(f"Episode directory already exists: {episode_dir}")

    # Site directory: sites/tgn/docs/14/ (no .0 for integers)
    site_dir = Path(SITE_ROOT, podcast_name, 'docs', ep_num_str).absolute()
    if not site_dir.exists():
        log.info(f"Creating site directory: {site_dir}")
        site_dir.mkdir(parents=True, exist_ok=True)
    else:
        log.debug(f"Site directory already exists: {site_dir}")

    return episode_dir, site_dir


@task(
    name="download-mp3",
    retries=3,
    retry_delay_seconds=120,  # 2 minute delay between retries
    cache_policy=INPUTS,
    log_prints=True
)
def download_mp3(episode_dir: Path, mp3_url: str) -> Path:
    """
    Download MP3 file for an episode.

    Args:
        episode_dir: Episode directory path
        mp3_url: URL to download MP3 from

    Returns:
        Path to downloaded MP3 file

    Raises:
        subprocess.CalledProcessError: If wget fails
    """
    log = get_logger()
    mp3_path = episode_dir / "episode.mp3"

    if mp3_path.exists():
        log.info(f"MP3 already exists: {mp3_path}")
        return mp3_path

    log.info(f"Downloading MP3 from {mp3_url}")
    log.debug(f"Saving to {mp3_path}")

    # Use wget like the Makefile does
    # -nc: no clobber (skip if exists)
    # --no-use-server-timestamps: don't set local file timestamp to server's
    result = subprocess.run(
        ['wget', '-nc', '--no-use-server-timestamps', '-O', str(mp3_path), mp3_url],
        capture_output=True,
        text=True,
        cwd=episode_dir
    )

    if result.returncode != 0:
        log.error(f"wget failed with return code {result.returncode}")
        log.error(f"Command: {' '.join(result.args)}")
        log.error(f"URL: {mp3_url}")
        if result.stdout:
            log.error(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            log.error(f"STDERR:\n{result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

    log.info(f"Downloaded MP3: {mp3_path} ({mp3_path.stat().st_size} bytes)")
    return mp3_path


@task(
    name="download-episode-html",
    retries=3,
    retry_delay_seconds=120,  # 2 minute delay between retries
    cache_policy=INPUTS,
    log_prints=True
)
def download_episode_html(episode_dir: Path, episode_url: str) -> Path:
    """
    Download episode HTML page.

    Args:
        episode_dir: Episode directory path
        episode_url: URL to download HTML from

    Returns:
        Path to downloaded HTML file, or None if download failed
    """
    log = get_logger()
    html_path = episode_dir / "episode.html"

    if html_path.exists():
        log.info(f"HTML already exists: {html_path}")
        return html_path

    log.info(f"Downloading episode HTML from {episode_url}")

    # Use wget with retry on 429 (rate limit) errors
    # --convert-links: convert links for local viewing
    # --retry-on-http-error=429: retry on rate limit
    # --wait=5 --random-wait: wait 5-10 seconds between retries
    result = subprocess.run(
        ['wget', '-O', str(html_path), '--convert-links',
         '--retry-on-http-error=429', '--wait=5', '--random-wait',
         episode_url],
        capture_output=True,
        text=True,
        cwd=episode_dir
    )

    # HTML download is best-effort, don't fail if it doesn't work
    if result.returncode != 0:
        log.warning(f"HTML download failed (non-fatal): {result.stderr}")
        return None

    log.info(f"Downloaded HTML: {html_path}")
    return html_path
