#!/usr/bin/env python3
"""
Rebuild all podcast sites with updated episode frontmatter.
"""
import sys
from loguru import logger as log

log.remove()
log.add(sys.stdout, level="INFO")

from models.podcast import get_all_podcasts
from flows.podcast import generate_and_deploy_site

if __name__ == "__main__":
    log.info("Rebuilding all podcast sites with search exclusions")
    log.info("=" * 60)

    podcasts = get_all_podcasts()

    for podcast in podcasts:
        log.info(f"Building and deploying {podcast.name}...")
        generate_and_deploy_site(podcast)
        log.success(f"{podcast.name} complete!")
        log.info("=" * 60)

    log.success("All podcast sites rebuilt and deployed!")
