#!/usr/bin/env python3
"""
RSS Feed Episode Numbers Processor

This script processes podcast RSS feeds to fill in missing episode numbers.
Episode numbers are inferred by sorting episodes chronologically and filling gaps sequentially.

Works with any podcast RSS feed that follows the iTunes podcast specification.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Tuple
from pathlib import Path
from loguru import logger as log


# XML namespaces used in RSS feeds
NAMESPACES = {
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'atom': 'http://www.w3.org/2005/Atom',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'googleplay': 'http://www.google.com/schemas/play-podcasts/1.0',
    'media': 'http://search.yahoo.com/mrss/',
    'podcast': 'https://podcastindex.org/namespace/1.0',
}


def register_namespaces():
    """Register all XML namespaces to preserve them in output."""
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)


def parse_pubdate(pubdate_str: str) -> datetime:
    """Parse RFC 2822 date format used in RSS feeds."""
    # Example: "Wed, 21 Jan 2026 16:00:00 +0000"
    return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")


def process_feed(input_path: Path, output_path: Path = None, verbose: bool = True) -> Tuple[int, int]:
    """
    Process RSS feed to fill in missing episode numbers.

    Args:
        input_path: Path to the RSS feed file to process
        output_path: Path to write the modified feed (None = modify in place)
        verbose: If True, print status messages

    Returns:
        Tuple of (total_episodes, episodes_modified)
    """
    register_namespaces()

    # Parse the XML
    tree = ET.parse(input_path)
    root = tree.getroot()

    # Find all items (episodes)
    items = root.findall('.//item')

    if verbose:
        log.info(f"Found {len(items)} total episodes in {input_path.name}")

    # Extract episode data: (item_element, pubdate, episode_number or None)
    episodes_data = []
    for item in items:
        pubdate_elem = item.find('pubDate')
        episode_elem = item.find('itunes:episode', NAMESPACES)
        title_elem = item.find('title')

        if pubdate_elem is None:
            if verbose:
                log.warning(f"Episode '{title_elem.text if title_elem is not None else 'Unknown'}' has no pubDate, skipping")
            continue

        pubdate = parse_pubdate(pubdate_elem.text)
        episode_num = int(episode_elem.text) if episode_elem is not None else None

        episodes_data.append({
            'item': item,
            'pubdate': pubdate,
            'episode_num': episode_num,
            'title': title_elem.text if title_elem is not None else 'Unknown'
        })

    # Sort by pubdate (oldest first)
    episodes_data.sort(key=lambda x: x['pubdate'])

    # Find the highest episode number to understand the sequence
    known_episodes = [(i, ep) for i, ep in enumerate(episodes_data) if ep['episode_num'] is not None]

    if not known_episodes:
        if verbose:
            log.warning("No episodes have episode numbers. Will assign numbers chronologically starting from 1.")
    else:
        if verbose:
            log.info(f"Found {len(known_episodes)} episodes with existing episode numbers")
            log.info(f"Missing episode numbers: {len(episodes_data) - len(known_episodes)}")

    # Infer episode numbers for missing ones
    # Strategy: Use chronological order and fill in gaps with available numbers
    # Collect all existing episode numbers first
    used_numbers = set(ep['episode_num'] for ep in episodes_data if ep['episode_num'] is not None)

    # Find next available number starting from 1
    next_number = 1
    modified_count = 0

    for position, ep_data in enumerate(episodes_data):
        if ep_data['episode_num'] is None:
            # Find next available number
            while next_number in used_numbers:
                next_number += 1

            # Assign this number
            item = ep_data['item']

            # Find or create itunes:episode element
            episode_elem = item.find('itunes:episode', NAMESPACES)
            if episode_elem is None:
                # Insert before episodeType if it exists, otherwise at the end
                episode_type_elem = item.find('itunes:episodeType', NAMESPACES)
                if episode_type_elem is not None:
                    # Insert before episodeType
                    idx = list(item).index(episode_type_elem)
                    episode_elem = ET.Element(f"{{{NAMESPACES['itunes']}}}episode")
                    item.insert(idx, episode_elem)
                else:
                    # Add at the end
                    episode_elem = ET.SubElement(item, f"{{{NAMESPACES['itunes']}}}episode")

            episode_elem.text = str(next_number)
            used_numbers.add(next_number)
            modified_count += 1

            if verbose:
                log.debug(f"  Added episode #{next_number}: {ep_data['title'][:60]}...")

            next_number += 1

    # Write modified XML
    if output_path is None:
        output_path = input_path

    # Write with XML declaration
    tree.write(output_path, encoding='UTF-8', xml_declaration=True)

    if verbose:
        log.info(f"Wrote modified feed to {output_path}")
        log.info(f"Modified {modified_count} episodes")

    return len(items), modified_count


if __name__ == "__main__":
    # Simple standalone usage
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='Process podcast RSS feed to fill in missing episode numbers'
    )
    parser.add_argument('feed_file', type=str, help='RSS feed file to process')
    parser.add_argument('-o', '--output', type=str, help='Output file (default: modify in place)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress output')

    args = parser.parse_args()

    input_path = Path(args.feed_file)
    if not input_path.exists():
        print(f"Error: File {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else None

    try:
        total, modified = process_feed(input_path, output_path, verbose=not args.quiet)
        if not args.quiet:
            log.info(f"Done! Processed {total} episodes, modified {modified}")
    except Exception as e:
        log.error(f"Error: {e}")
        sys.exit(1)
