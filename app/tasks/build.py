"""Prefect tasks for building and deploying podcast sites."""
import subprocess
import sys
import shutil
from pathlib import Path
from prefect import task
from prefect import get_run_logger
import pagefind_bin

from constants import SITE_ROOT


@task(
    name="update-episodes-index",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def update_episodes_index(podcast_name: str, episodes_data: list[dict]) -> Path:
    """
    Update episodes.md index file with episode listings.

    Args:
        podcast_name: Name of the podcast
        episodes_data: List of episode data dictionaries

    Returns:
        Path to episodes.md file
    """
    log = get_run_logger()
    from datetime import datetime

    episodes_md = Path(SITE_ROOT, podcast_name, 'docs', 'episodes.md')

    # Generate index content
    ts = datetime.now().astimezone().isoformat()
    content = f"### Page updated {ts} - {len(episodes_data)} episodes\n"

    # Add each episode as a link
    for ep_data in sorted(episodes_data, key=lambda x: x.get('number', 0)):
        ep_num = ep_data.get('number')
        title = ep_data.get('title', 'Unknown')
        pub_date = ep_data.get('pub_date', '')
        content += f"- [{title}]({str(ep_num)}/episode.md) {pub_date}\n"

    episodes_md.write_text(content)
    log.success(f"Updated episodes index: {episodes_md}")
    return episodes_md


@task(
    name="build-site",
    retries=2,
    retry_delay_seconds=60,
    log_prints=True
)
def build_site(podcast_name: str) -> Path:
    """
    Build static site with zensical.

    Args:
        podcast_name: Name of the podcast

    Returns:
        Path to built site directory

    Raises:
        subprocess.CalledProcessError: If zensical build fails
    """
    log = get_run_logger()
    site_dir = Path(SITE_ROOT, podcast_name)
    site_output = site_dir / 'site'

    log.info(f"Building site for {podcast_name} with zensical")
    log.debug(f"Site directory: {site_dir}")

    # Find zensical - check virtualenv first
    venv_bin = Path(sys.executable).parent / 'zensical'
    log.debug(f"Checking for zensical at: {venv_bin}")
    log.debug(f"sys.executable: {sys.executable}")
    log.debug(f"venv_bin exists: {venv_bin.exists()}")

    if venv_bin.exists():
        zensical_bin = str(venv_bin)
        log.debug(f"Found zensical in virtualenv: {zensical_bin}")
    else:
        # Fall back to PATH
        log.debug("zensical not in virtualenv, checking PATH")
        zensical_bin = shutil.which('zensical')
        if not zensical_bin:
            raise FileNotFoundError(f"zensical not found in virtualenv ({venv_bin}) or PATH")
        log.debug(f"Found zensical in PATH: {zensical_bin}")

    log.info(f"Using zensical: {zensical_bin}")

    # Run zensical build --clean
    result = subprocess.run(
        [zensical_bin, 'build', '--clean'],
        cwd=str(site_dir),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        log.error(f"zensical build failed with return code {result.returncode}")
        log.error(f"Command: {' '.join(result.args)}")
        if result.stdout:
            log.error(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            log.error(f"STDERR:\n{result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

    log.success(f"Site built successfully: {site_output}")
    return site_output


@task(
    name="generate-search-index",
    retries=2,
    retry_delay_seconds=60,
    log_prints=True
)
def generate_search_index(site_path: Path) -> bool:
    """
    Generate search index with Pagefind.

    Args:
        site_path: Path to built site directory

    Returns:
        True if search index generated successfully

    Raises:
        subprocess.CalledProcessError: If pagefind fails
    """
    log = get_run_logger()
    log.info(f"Generating search index with Pagefind for {site_path}")

    # Get pagefind binary path
    pagefind_bin_path = str(pagefind_bin.get_executable())

    # Run pagefind on the built site
    # Use glob pattern to only index index.html files (generated content)
    # This excludes episode.html files (downloaded web page snapshots)
    result = subprocess.run(
        [pagefind_bin_path, '--site', str(site_path), '--glob', '**/index.html'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        log.error(f"Pagefind failed with return code {result.returncode}")
        log.error(f"Command: {' '.join(result.args)}")
        if result.stdout:
            log.error(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            log.error(f"STDERR:\n{result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

    log.success("Search index generated successfully")
    return True


@task(
    name="deploy-site",
    retries=2,
    retry_delay_seconds=60,
    log_prints=True
)
def deploy_site(podcast_name: str, site_path: Path) -> bool:
    """
    Deploy site to caddy2 static hosting via rsync.

    Args:
        podcast_name: Name of the podcast
        site_path: Path to built site directory

    Returns:
        True if deployment succeeded

    Raises:
        subprocess.CalledProcessError: If rsync fails
    """
    log = get_run_logger()
    deploy_target = f"/usr/local/www/{podcast_name}"

    log.info(f"Deploying {podcast_name} site to {deploy_target}")
    log.debug(f"Source: {site_path}")

    # Run rsync with same options as Makefile
    # -q: quiet
    # -r: recursive
    # -p: preserve permissions
    # -g: preserve group
    # -D: preserve device files and special files
    # --delete: delete files in destination that aren't in source
    # --force: force deletion of directories
    result = subprocess.run(
        ['rsync', '-qrpgD', '--delete', '--force', f'{site_path}/', deploy_target],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        log.error(f"rsync deployment failed with return code {result.returncode}")
        log.error(f"Command: {' '.join(result.args)}")
        if result.stdout:
            log.error(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            log.error(f"STDERR:\n{result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

    log.success(f"Site deployed successfully to {deploy_target}")
    return True
