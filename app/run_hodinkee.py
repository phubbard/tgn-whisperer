#!/usr/bin/env python3
"""
Run Prefect workflow for Hodinkee podcast only (for testing).
"""
import sys
from loguru import logger as log

# Set up logging
log.remove()
log.add(sys.stdout, level="INFO")

from prefect import tags
from models.podcast import get_all_podcasts
from flows.podcast import process_podcast

if __name__ == "__main__":
    log.info("Processing Hodinkee podcast via Prefect")
    log.info("=" * 60)

    # Get Hodinkee podcast config
    podcasts = get_all_podcasts()
    hodinkee = [p for p in podcasts if p.name == 'hodinkee'][0]

    log.info(f"Podcast: {hodinkee.name}")
    log.info(f"RSS: {hodinkee.rss_url}")
    log.info(f"Emails: {hodinkee.emails}")
    log.info("=" * 60)

    # Run the flow with tags
    with tags("hodinkee", "podcast"):
        result = process_podcast(hodinkee)

    log.info("=" * 60)
    if result:
        log.success(f"Processed {len(result)} new episodes: {result}")
    else:
        log.info("No new episodes found")
