#!/usr/bin/env python3
"""
Run Prefect workflow for a single episode (for testing).

Usage: python run_single_episode.py hodinkee 91
"""
import sys
from loguru import logger as log

if len(sys.argv) != 3:
    print("Usage: python run_single_episode.py <podcast> <episode_number>")
    print("Example: python run_single_episode.py hodinkee 91")
    sys.exit(1)

# Set up logging
log.remove()
log.add(sys.stdout, level="INFO")

podcast_name = sys.argv[1]
episode_number = float(sys.argv[2])

from models.podcast import get_all_podcasts
from tasks.rss import fetch_rss_feed, process_rss_feed, get_episode_details, parse_episode_data
from flows.episode import process_episode

if __name__ == "__main__":
    log.info(f"Processing single episode: {podcast_name} #{episode_number}")
    log.info("=" * 60)

    # Get podcast config
    podcasts = get_all_podcasts()
    podcast = [p for p in podcasts if p.name == podcast_name][0]

    # Fetch and process RSS feed
    log.info("Fetching RSS feed...")
    rss_content = fetch_rss_feed(podcast)

    log.info("Processing RSS feed...")
    feed_data = process_rss_feed(rss_content, podcast.name)
    episodes = feed_data['episodes']

    # Get episode details
    log.info(f"Looking for episode {episode_number}...")
    episode_entry = get_episode_details.fn(episodes, episode_number)

    if not episode_entry:
        log.error(f"Episode {episode_number} not found in feed!")
        sys.exit(1)

    episode_data = parse_episode_data(episode_entry)
    log.info(f"Found: {episode_data['title']}")
    log.info("=" * 60)

    # Process the episode
    result = process_episode(podcast, episode_entry)

    log.info("=" * 60)
    log.success(f"Episode processing complete: {result}")
