"""Prefect tasks for RSS feed fetching and processing."""
import json
import xmltodict
from pathlib import Path
from prefect import task
from prefect.cache_policies import INPUTS
from utils.logging import get_logger
import requests

from models.podcast import Podcast
from rss_processor import process_feed


@task(
    name="fetch-rss-feed",
    retries=3,
    retry_delay_seconds=60,  # 60 second delay between retries
    cache_policy=INPUTS,
    log_prints=True
)
def fetch_rss_feed(podcast: Podcast) -> str:
    """
    Fetch RSS feed from URL.

    Args:
        podcast: Podcast configuration object

    Returns:
        RSS feed content as string

    Raises:
        requests.HTTPError: If the request fails
    """
    log = get_logger()
    log.info(f"Fetching RSS feed for {podcast.name}: {podcast.rss_url}")

    # Identify ourselves to avoid 403 errors
    headers = {
        'User-Agent': 'tgn-whisperer https://github.com/phubbard/tgn-whisperer/',
        'From': 'pfh@phfactor.net'
    }

    response = requests.get(podcast.rss_url, headers=headers)

    if not response.ok:
        log.error(f"Error fetching RSS feed: {response.status_code} {response.reason}")
        response.raise_for_status()

    log.info(f"Successfully fetched RSS feed for {podcast.name} ({len(response.text)} bytes)")
    return response.text


@task(
    name="process-rss-feed",
    retries=2,
    retry_delay_seconds=60,
    cache_policy=INPUTS,
    log_prints=True
)
def process_rss_feed(rss_content: str, podcast_name: str) -> dict:
    """
    Process RSS feed to fill in missing episode numbers and parse XML.

    Args:
        rss_content: RSS feed XML content as string
        podcast_name: Name of the podcast (for file naming)

    Returns:
        Dictionary with:
        - 'episodes': list of episode entry dictionaries
        - 'total_count': total number of episodes
        - 'modified_count': number of episodes that had episode numbers added

    Raises:
        Exception: If XML parsing fails
    """
    log = get_logger()
    log.info(f"Processing RSS feed for {podcast_name}")

    # Save RSS to disk for processing (rss_processor needs file path)
    feed_file = Path(f'{podcast_name}_feed.rss')
    log.debug(f"Saving {podcast_name} feed to {feed_file} for processing")
    feed_file.write_text(rss_content)

    # Process the feed to add missing episode numbers
    total, modified = process_feed(feed_file, verbose=False)
    if modified > 0:
        log.info(f"{podcast_name} feed processed: {total} episodes, {modified} modified")
    else:
        log.debug(f"{podcast_name} feed already complete: {total} episodes")

    # Read the modified feed back and parse it
    feed_text = feed_file.read_text()
    log.debug("Parsing XML")
    entries = xmltodict.parse(feed_text)

    episodes = entries['rss']['channel']['item']
    if not isinstance(episodes, list):
        # Handle single-episode case
        episodes = [episodes]

    log.info(f"Parsed {len(episodes)} episodes from {podcast_name} feed")

    return {
        'episodes': episodes,
        'total_count': total,
        'modified_count': modified
    }


def _episode_number_from_rss(entry: dict) -> float:
    """
    Extract episode number from RSS entry.

    After processing feeds with rss_processor, all episodes should have
    itunes:episode tags, so we can simply read them directly.

    Args:
        entry: RSS item entry dictionary

    Returns:
        Episode number as float, or None if not found
    """
    meta_entry = entry.get('itunes:episode', None)
    if meta_entry:
        return float(meta_entry)
    return None


@task(
    name="check-new-episodes",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def check_new_episodes(podcast_name: str, episodes: list[dict]) -> list[float]:
    """
    Check for new episodes by comparing current feed to saved notification list.

    Args:
        podcast_name: Name of the podcast
        episodes: List of episode entry dictionaries from RSS feed

    Returns:
        List of new episode numbers (floats)
    """
    log = get_logger()
    log.info(f"Checking for new episodes in {podcast_name}")

    # Extract episode numbers from current feed
    current_ep_numbers = set()
    fail_count = 0

    for entry in episodes:
        ep_number = _episode_number_from_rss(entry)
        if ep_number is None:
            fail_count += 1
            log.warning(f"Could not extract episode number from entry: {entry.get('title', 'Unknown')}")
        else:
            current_ep_numbers.add(ep_number)

    if fail_count:
        log.error(f"Failed to extract episode numbers for {fail_count} episodes")
        raise ValueError(f"UN-DISCERNIBLE EPISODES: {fail_count} episodes missing numbers")

    log.debug(f"Found {len(current_ep_numbers)} episodes in current feed")

    # Load saved notification list
    filename = Path(f'{podcast_name}-notified.json')
    try:
        old_list = json.load(open(filename, 'r'))
        log.debug(f"Loaded {len(old_list)} previously notified episodes from {filename}")
    except FileNotFoundError:
        log.warning(f'Saved file {filename} not found, treating all episodes as new')
        old_list = []

    # Find new episodes
    old_eps = set(old_list)
    new_eps = current_ep_numbers.difference(old_eps)
    new_count = len(new_eps)

    if not new_count:
        log.info(f"No new episodes found in {podcast_name}")
        return []

    log.info(f"{new_count} new episodes found in {podcast_name}: {sorted(new_eps)}")

    # Save updated list
    all_eps = old_eps.union(current_ep_numbers)
    log.info(f"Saving updated notification list to {filename}")
    json.dump(list(all_eps), open(filename, 'w'))

    return sorted(list(new_eps))


@task(
    name="get-episode-details",
    log_prints=True
)
def get_episode_details(episodes: list[dict], episode_number: float) -> dict:
    """
    Get detailed information for a specific episode from the feed.

    Args:
        episodes: List of episode entry dictionaries from RSS feed
        episode_number: Episode number to look up

    Returns:
        Episode entry dictionary, or None if not found
    """
    log = get_logger()
    for entry in episodes:
        ep_num = _episode_number_from_rss(entry)
        if ep_num == episode_number:
            return entry

    log.warning(f"Episode {episode_number} not found in feed")
    return None


def _unwrap_bitly(url: str) -> str:
    """
    Unwrap bit.ly URLs using lookup dictionary.

    Args:
        url: URL that may be a bit.ly shortlink

    Returns:
        Resolved URL or original URL if not in lookup
    """
    import json
    from pathlib import Path

    if 'bit.ly' not in url.lower():
        return url

    # Load bitly mapping
    bitly_path = Path('./bitly.json')
    if not bitly_path.exists():
        bitly_path = Path('./app/bitly.json')

    if bitly_path.exists():
        lookup_map = json.load(open(bitly_path, 'r'))
        if url in lookup_map:
            return lookup_map[url]
        else:
            log.warning(f"bit.ly URL not found in lookup: {url}")
    else:
        log.warning(f"bitly.json not found, returning original URL: {url}")

    return url


def _extract_episode_url(entry: dict, default_url: str = 'https://thegreynato.com/') -> str:
    """
    Extract episode URL from RSS entry.

    Args:
        entry: RSS item entry dictionary
        default_url: Default URL to return if none found

    Returns:
        Episode URL
    """
    import re

    # Priority 1: 'link' field in RSS
    if 'link' in entry:
        return entry['link']

    # Priority 2: Search description for URL
    log.debug("No proper URL found, searching description")
    url_pattern = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    url_matcher = re.compile(url_pattern)

    if 'description' in entry:
        match = url_matcher.search(entry['description'])
        if match:
            log.debug(f"Found URL in description: {match[0]}")
            return match[0]

    log.warning(f"No episode URL found, returning default: {default_url}")
    return default_url


@task(
    name="parse-episode-data",
    log_prints=True
)
def parse_episode_data(entry: dict) -> dict:
    """
    Parse RSS entry into episode data dictionary.

    Args:
        entry: RSS item entry dictionary

    Returns:
        Episode data dictionary with all fields needed for processing
    """
    log = get_logger()
    episode_number = _episode_number_from_rss(entry)

    # Extract basic fields
    episode_url = _extract_episode_url(entry)
    episode_url = _unwrap_bitly(episode_url)

    episode_data = {
        'number': episode_number,
        'title': entry.get('title', 'Unknown'),
        'subtitle': entry.get('subtitle', entry.get('itunes:subtitle', '')),
        'mp3_url': entry.get('enclosure', {}).get('@url', ''),
        'episode_url': episode_url,
        'pub_date': entry.get('pubDate', ''),
    }

    log.debug(f"Parsed episode {episode_number}: {episode_data['title']}")
    return episode_data
