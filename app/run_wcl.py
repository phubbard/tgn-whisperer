#!/usr/bin/env python3
"""
Run Prefect workflow for WCL (40&20) podcast only (for testing).
"""
import sys

from dotenv import load_dotenv
from loguru import logger as log

load_dotenv()

# Set up logging
log.remove()
log.add(sys.stdout, level="INFO")

from prefect import tags
from models.podcast import get_all_podcasts
from flows.podcast import process_podcast

if __name__ == "__main__":
    log.info("Processing WCL (40&20) podcast via Prefect")
    log.info("=" * 60)

    # Get WCL podcast config
    podcasts = get_all_podcasts()
    wcl = [p for p in podcasts if p.name == 'wcl'][0]

    log.info(f"Podcast: {wcl.name}")
    log.info(f"RSS: {wcl.rss_url}")
    log.info(f"Emails: {wcl.emails}")
    log.info("=" * 60)

    # Run the flow with tags
    with tags("wcl", "podcast"):
        result = process_podcast(wcl)

    log.info("=" * 60)
    if result:
        log.success(f"Processed {len(result)} new episodes: {result}")
    else:
        log.info("No new episodes found")
