#!/usr/bin/env python3
"""
Update RSS test fixtures by downloading latest feeds.

Usage:
    # Download latest feeds (full size)
    python update_fixtures.py

    # Download and strip to N posts (removes episode numbers for testing)
    python update_fixtures.py --keep-posts=2
"""

import argparse
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

# RSS feed URLs
FEEDS = {
    'tgn.rss': 'https://feeds.buzzsprout.com/2049759.rss',
    'wcl.rss': 'https://feed.podbean.com/the40and20podcast/feed.xml',
    'hodinkee.rss': 'https://feeds.simplecast.com/OzTmhziA',
}

# Namespaces used in podcast RSS feeds
NAMESPACES = {
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
}

# Register namespaces to preserve them when writing
def register_namespaces():
    ET.register_namespace('', 'http://www.w3.org/2005/Atom')
    ET.register_namespace('itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
    ET.register_namespace('content', 'http://purl.org/rss/1.0/modules/content/')
    ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')
    ET.register_namespace('podcast', 'https://podcastindex.org/namespace/1.0')
    ET.register_namespace('googleplay', 'http://www.google.com/schemas/play-podcasts/1.0')
    ET.register_namespace('media', 'http://search.yahoo.com/mrss/')
    ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')


def download_feed(url: str, dest: Path) -> None:
    """Download an RSS feed using curl."""
    subprocess.run(
        ['curl', '-sL', '-A', 'Mozilla/5.0 (compatible; TGN-Whisperer/1.0)', url, '-o', str(dest)],
        check=True
    )


def strip_feed(feed_path: Path, keep_items: int) -> None:
    """Keep only N items and remove episode numbers for testing."""
    register_namespaces()

    tree = ET.parse(feed_path)
    root = tree.getroot()

    channel = root.find('channel')
    if channel is None:
        print(f"  Warning: No channel found in {feed_path}")
        return

    items = channel.findall('item')
    original_count = len(items)

    # Remove all but first N items
    for item in items[keep_items:]:
        channel.remove(item)

    # Remove itunes:episode from remaining items so processor will renumber
    remaining_items = channel.findall('item')
    removed_numbers = 0
    for item in remaining_items:
        episode_elem = item.find('itunes:episode', NAMESPACES)
        if episode_elem is not None:
            item.remove(episode_elem)
            removed_numbers += 1

    tree.write(feed_path, encoding='UTF-8', xml_declaration=True)

    print(f"  Stripped {original_count} -> {keep_items} items, removed {removed_numbers} episode numbers")


def main():
    parser = argparse.ArgumentParser(
        description='Update RSS test fixtures by downloading latest feeds.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Download latest feeds (full size):
    python update_fixtures.py

  Download and strip to 2 posts for testing:
    python update_fixtures.py --keep-posts=2
        """
    )
    parser.add_argument(
        '--keep-posts',
        type=int,
        default=None,
        metavar='N',
        help='Strip feeds to N posts and remove episode numbers (for smaller test fixtures)'
    )

    args = parser.parse_args()

    # Get directory where this script lives
    script_dir = Path(__file__).parent

    print("Updating RSS test fixtures...")

    for filename, url in FEEDS.items():
        dest = script_dir / filename
        print(f"\n{filename}:")
        print(f"  Downloading from {url}")
        download_feed(url, dest)

        size = dest.stat().st_size
        print(f"  Downloaded {size:,} bytes")

        if args.keep_posts is not None:
            strip_feed(dest, args.keep_posts)
            size = dest.stat().st_size
            print(f"  Final size: {size:,} bytes")

    print("\nDone!")


if __name__ == '__main__':
    main()
