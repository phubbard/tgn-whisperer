#!/usr/bin/env python3
"""
Run Prefect workflow for TGN podcast only (for testing).
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
from flows.podcast import generate_and_deploy_site

if __name__ == "__main__":
    log.info("Generating and deploying TGN site")
    log.info("=" * 60)

    # Get TGN podcast config
    podcasts = get_all_podcasts()
    tgn = [p for p in podcasts if p.name == 'tgn'][0]

    log.info(f"Podcast: {tgn.name}")
    log.info("=" * 60)

    # Run the deployment flow with tags
    with tags("tgn", "podcast", "deploy"):
        generate_and_deploy_site(tgn)

    log.success("TGN site deployed")
