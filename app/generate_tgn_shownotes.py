#!/usr/bin/env python3
"""
Generate TGN shownotes by extracting and scraping related links from episode pages.
"""

import sys
from pathlib import Path
from loguru import logger as log

# Import from the related_links_collector package
from related_links_collector.extract_rss_urls import extract_urls_from_rss
from related_links_collector.scrape import run as scrape_run
from related_links_collector.generate_markdown import generate_markdown


def main():
    """
    Complete workflow to generate TGN shownotes:
    1. Extract episode URLs from RSS feed
    2. Scrape related links from each episode page
    3. Generate markdown document
    """
    # Set up paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'app' / 'data'
    data_dir.mkdir(exist_ok=True)

    rss_path = project_root / 'tgn_feed.rss'
    urls_file = data_dir / 'tgn_urls.txt'
    related_file = data_dir / 'tgn_related.jsonl'
    exceptions_file = data_dir / 'tgn_exceptions.jsonl'
    output_file = project_root / 'sites' / 'tgn' / 'docs' / 'shownotes.md'

    # Check that RSS feed exists
    if not rss_path.exists():
        log.error(f"RSS feed not found: {rss_path}")
        sys.exit(1)

    log.info("Step 1: Extracting episode URLs from RSS feed")
    extract_urls_from_rss(str(rss_path), str(urls_file), log=log)

    log.info("Step 2: Scraping related links from episode pages")
    # Use the scrape run function
    scrape_run(
        urls_path=str(urls_file),
        out_path=str(related_file),
        exceptions_path=str(exceptions_file),
        overrides_path=None,
        rate=1.2,
        log=log
    )

    log.info("Step 3: Generating markdown document")
    generate_markdown(
        rss_path=str(rss_path),
        jsonl_path=str(related_file),
        output_path=str(output_file),
        log=log
    )

    log.success(f"Shownotes generated successfully: {output_file}")
    print(f"\nShownotes written to: {output_file}")


if __name__ == '__main__':
    main()
