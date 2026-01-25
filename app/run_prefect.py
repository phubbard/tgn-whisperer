#!/usr/bin/env python3
"""
Run the Prefect podcast processing workflow.

This can be run directly without a Prefect server for testing.
"""
import sys

from dotenv import load_dotenv
from loguru import logger as log

load_dotenv()

# Set up logging
log.remove()
log.add(sys.stdout, level="INFO")

# Import the main flow
from flows.main import process_all_podcasts

if __name__ == "__main__":
    log.info("Starting podcast processing workflow via Prefect")
    log.info("=" * 60)

    # Run the flow
    # Note: Running without a Prefect server means no UI, but it will still work
    result = process_all_podcasts()

    log.info("=" * 60)
    log.success("Workflow complete!")

    if result:
        log.info(f"Processed episodes: {result}")
