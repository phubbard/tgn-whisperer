#!/usr/bin/env python3
"""
Test script for RSS processing workflow.

This tests the RSS fetching and processing flow without running the full pipeline.
"""
from pathlib import Path
from loguru import logger as log

from models.podcast import get_all_podcasts
from tasks.rss import fetch_rss_feed, process_rss_feed, check_new_episodes


def test_rss_workflow():
    """Test RSS workflow with TGN podcast."""
    log.info("Testing RSS workflow")

    # Get TGN podcast config
    podcasts = get_all_podcasts()
    tgn = podcasts[0]  # TGN is first in list

    log.info(f"Testing with podcast: {tgn.name}")

    # Step 1: Fetch RSS feed
    log.info("Step 1: Fetching RSS feed...")
    rss_content = fetch_rss_feed.fn(tgn)  # Use .fn to call without Prefect context
    log.success(f"Fetched {len(rss_content)} bytes")

    # Step 2: Process feed
    log.info("Step 2: Processing feed...")
    feed_data = process_rss_feed.fn(rss_content, tgn.name)
    log.success(f"Parsed {feed_data['total_count']} episodes, {feed_data['modified_count']} modified")

    # Step 3: Check for new episodes
    log.info("Step 3: Checking for new episodes...")
    new_eps = check_new_episodes.fn(tgn.name, feed_data['episodes'])

    if new_eps:
        log.success(f"Found {len(new_eps)} new episodes: {new_eps}")
    else:
        log.info("No new episodes found")

    # Verify RSS file was created
    feed_file = Path(f"{tgn.name}_feed.rss")
    if feed_file.exists():
        log.success(f"RSS file created: {feed_file}")
    else:
        log.error(f"RSS file not found: {feed_file}")

    log.success("RSS workflow test completed successfully!")


if __name__ == '__main__':
    test_rss_workflow()
