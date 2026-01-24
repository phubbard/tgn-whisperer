#!/usr/bin/env python3
"""
Check what episode numbers are actually in the RSS feeds' itunes:episode tags.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from loguru import logger as log
import xmltodict

NAMESPACES = {
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
}


def analyze_feed(name: str, feed_path: Path):
    """Analyze what episode numbers exist in RSS feed."""
    log.info(f"\n{'='*80}")
    log.info(f"Analyzing {name}")
    log.info(f"{'='*80}")

    # Parse with xmltodict (like process.py)
    with open(feed_path, 'r') as f:
        entries = xmltodict.parse(f.read())

    total = len(entries['rss']['channel']['item'])
    with_numbers = 0
    without_numbers = 0

    log.info(f"Total episodes: {total}")

    for entry in entries['rss']['channel']['item']:
        title = entry['title']
        itunes_ep = entry.get('itunes:episode', None)

        if itunes_ep:
            with_numbers += 1
        else:
            without_numbers += 1
            log.warning(f"  Missing itunes:episode: {title[:70]}")

    log.info(f"\nWith itunes:episode tags: {with_numbers}")
    log.info(f"Without itunes:episode tags: {without_numbers}")

    if without_numbers == 0:
        log.info("✓ All episodes have itunes:episode tags!")
    else:
        log.warning(f"⚠ {without_numbers} episodes need numbering")

    return without_numbers


def main():
    log.remove()
    log.add(lambda msg: print(msg, end=''), level="INFO")

    test_dir = Path('test_feeds')

    total_missing = 0

    total_missing += analyze_feed('TGN', test_dir / 'tgn.rss')
    total_missing += analyze_feed('WCL', test_dir / 'wcl.rss')
    total_missing += analyze_feed('Hodinkee', test_dir / 'hodinkee.rss')

    log.info(f"\n{'='*80}")
    log.info(f"SUMMARY")
    log.info(f"{'='*80}")
    log.info(f"Total episodes missing itunes:episode tags: {total_missing}")


if __name__ == "__main__":
    main()
