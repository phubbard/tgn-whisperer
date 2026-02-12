#!/usr/bin/env python3
"""
RSS Feed Episode Numbers Processor

This script processes podcast RSS feeds to fill in missing episode numbers.
Episode numbers are inferred by sorting episodes chronologically and filling gaps sequentially.

Works with any podcast RSS feed that follows the iTunes podcast specification.
"""

import re
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


def extract_tgn_episode_number(title: str) -> int | None:
    """
    Extract episode number from a TGN episode title.

    TGN uses hand-authored episode numbers in titles. This function parses
    various title formats used over the show's history.

    Args:
        title: Episode title string

    Returns:
        Episode number as int, or None for unnumbered episodes
    """
    # Skip known unnumbered episode types
    if re.search(r'Re-Reupload', title):
        return None

    # Modern format (episode 118+): "The Grey NATO – 363 –" or "– 300!"
    m = re.search(r'Grey\s+NAT[Oo]\s*[-–—]+\s*(\d+)\s*[-–—!]', title)
    if m:
        return int(m.group(1))

    # Modern format trailing: "The Grey NATO – 300!" (number at end after dash)
    m = re.search(r'Grey\s+NAT[Oo]\s*[-–—]+\s*(\d+)\s*!?\s*$', title)
    if m:
        return int(m.group(1))

    # Early format with Ep/EP/Episode prefix: "EP 14", "Ep 61", "Episode 01"
    m = re.search(r'[Ee][Pp](?:isode)?\s*(\d+)', title)
    if m:
        return int(m.group(1))

    # Early format without Ep prefix: "The Grey Nato - 02 - Origin Stories"
    m = re.search(r'Grey\s+Nat[oa]\s*-\s*(\d+)\s*-', title)
    if m:
        return int(m.group(1))

    return None


def _set_episode_number(item, episode_num: float):
    """Set or create the itunes:episode element on an RSS item."""
    episode_elem = item.find('itunes:episode', NAMESPACES)
    if episode_elem is None:
        episode_type_elem = item.find('itunes:episodeType', NAMESPACES)
        if episode_type_elem is not None:
            idx = list(item).index(episode_type_elem)
            episode_elem = ET.Element(f"{{{NAMESPACES['itunes']}}}episode")
            item.insert(idx, episode_elem)
        else:
            episode_elem = ET.SubElement(item, f"{{{NAMESPACES['itunes']}}}episode")

    from constants import format_episode_number
    episode_elem.text = format_episode_number(episode_num)


def _process_tgn_episodes(episodes_data: list, verbose: bool) -> int:
    """
    Process TGN episodes using title-based numbering.

    TGN's Buzzsprout feed has wrong sequential itunes:episode tags.
    The real episode numbers are in the titles. Unnumbered episodes
    (TGN Chats, Depth Charge, Out Of Office, specials) get fractional numbers.
    """
    # Step 1: Extract episode numbers from titles (ignoring itunes:episode tags)
    for ep in episodes_data:
        ep['title_num'] = extract_tgn_episode_number(ep['title'])

    # Step 2: Assign fractional numbers to unnumbered episodes
    for i, ep in enumerate(episodes_data):
        if ep['title_num'] is not None:
            continue

        # Find previous numbered episode
        prev_num = None
        for j in range(i - 1, -1, -1):
            if episodes_data[j]['title_num'] is not None:
                prev_num = episodes_data[j]['title_num']
                break

        # Find next numbered episode
        next_num = None
        for j in range(i + 1, len(episodes_data)):
            if episodes_data[j]['title_num'] is not None:
                next_num = episodes_data[j]['title_num']
                break

        if prev_num is not None and next_num is not None:
            if next_num - prev_num > 1:
                # Gap exists: fill with next integer
                ep['title_num'] = prev_num + 1
            else:
                # No gap: use fractional
                ep['title_num'] = prev_num + 0.5
        elif prev_num is not None:
            ep['title_num'] = prev_num + 0.5
        else:
            ep['title_num'] = 0.5

        if verbose:
            log.debug(f"  Assigned {ep['title_num']}: {ep['title'][:60]}...")

    # Step 3: Override all itunes:episode tags with correct numbers
    modified_count = 0
    for ep in episodes_data:
        new_num = ep['title_num']
        if ep['episode_num'] != new_num:
            modified_count += 1
        ep['episode_num'] = new_num
        _set_episode_number(ep['item'], new_num)

    if verbose:
        log.info(f"TGN: overrode {modified_count} episode numbers from titles")

    return modified_count


def _process_generic_episodes(episodes_data: list, verbose: bool) -> int:
    """Process non-TGN episodes using the original gap-filling strategy."""
    known_episodes = [(i, ep) for i, ep in enumerate(episodes_data) if ep['episode_num'] is not None]

    if not known_episodes:
        if verbose:
            log.warning("No episodes have episode numbers. Will assign numbers chronologically starting from 1.")
    else:
        if verbose:
            log.info(f"Found {len(known_episodes)} episodes with existing episode numbers")
            log.info(f"Missing episode numbers: {len(episodes_data) - len(known_episodes)}")

    used_numbers = set(ep['episode_num'] for ep in episodes_data if ep['episode_num'] is not None)
    next_number = 1
    modified_count = 0

    for ep_data in episodes_data:
        if ep_data['episode_num'] is None:
            while next_number in used_numbers:
                next_number += 1

            _set_episode_number(ep_data['item'], next_number)
            used_numbers.add(next_number)
            modified_count += 1

            if verbose:
                log.debug(f"  Added episode #{next_number}: {ep_data['title'][:60]}...")

            next_number += 1

    return modified_count


def process_feed(input_path: Path, output_path: Path = None, verbose: bool = True, podcast_name: str = None) -> Tuple[int, int]:
    """
    Process RSS feed to fill in missing episode numbers.

    Args:
        input_path: Path to the RSS feed file to process
        output_path: Path to write the modified feed (None = modify in place)
        verbose: If True, print status messages
        podcast_name: Podcast identifier. When 'tgn', uses title-based numbering
                      to override incorrect Buzzsprout sequential numbers.

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
        episode_num = float(episode_elem.text) if episode_elem is not None else None

        episodes_data.append({
            'item': item,
            'pubdate': pubdate,
            'episode_num': episode_num,
            'title': title_elem.text if title_elem is not None else 'Unknown'
        })

    # Sort by pubdate (oldest first)
    episodes_data.sort(key=lambda x: x['pubdate'])

    if podcast_name == 'tgn':
        modified_count = _process_tgn_episodes(episodes_data, verbose)
    else:
        modified_count = _process_generic_episodes(episodes_data, verbose)

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
