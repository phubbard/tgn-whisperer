"""Prefect tasks for checking episode completion status."""
from pathlib import Path
from prefect import task
from loguru import logger as log


@task(
    name="check-episode-completion",
    log_prints=True
)
def check_episode_completion(podcast_name: str, episode_number: float) -> bool:
    """
    Check if an episode has been fully processed.

    An episode is considered complete if it has an episode.md file in the site directory.

    Args:
        podcast_name: Name of the podcast
        episode_number: Episode number

    Returns:
        True if episode is fully processed, False otherwise
    """
    from constants import SITE_ROOT

    # Check for episode.md in the site directory
    site_dir = Path(SITE_ROOT, podcast_name, 'docs', str(episode_number))
    md_path = site_dir / "episode.md"

    if md_path.exists():
        log.debug(f"Episode {podcast_name} #{episode_number} is complete: {md_path} exists")
        return True
    else:
        log.debug(f"Episode {podcast_name} #{episode_number} is incomplete: {md_path} missing")
        return False


@task(
    name="filter-incomplete-episodes",
    log_prints=True
)
def filter_incomplete_episodes(podcast_name: str, episode_numbers: list[float]) -> list[float]:
    """
    Filter a list of episode numbers to only those that are incomplete.

    Args:
        podcast_name: Name of the podcast
        episode_numbers: List of episode numbers to check

    Returns:
        List of episode numbers that need processing (incomplete or missing)
    """
    incomplete = []

    log.info(f"Checking completion status for {len(episode_numbers)} episodes")

    for ep_num in episode_numbers:
        if not check_episode_completion.fn(podcast_name, ep_num):
            incomplete.append(ep_num)

    if incomplete:
        log.info(f"Found {len(incomplete)} incomplete episodes: {sorted(incomplete)}")
    else:
        log.info(f"All episodes are complete")

    return incomplete
