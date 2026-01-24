#!/usr/bin/env python3
"""
Compare hand-coded episode numbering vs chronological numbering for all three podcasts.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import re
import xmltodict
from loguru import logger as log

NAMESPACES = {
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
}


def parse_pubdate(pubdate_str: str) -> datetime:
    """Parse RFC 2822 date format used in RSS feeds."""
    return datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")


# OLD NUMBERING FUNCTIONS (from process.py)

def episode_number_hodinkee(entry):
    meta_entry = entry.get('itunes:episode', None)
    if meta_entry:
        return float(meta_entry)
    return None


def episode_number_wcl(entry):
    wcl_lookup = {
        "Watch Clicker Mini Review - Nodus Sector Dive": 81.5,
        "Episode 36 GMT Watches": 36,
    }
    meta_entry = entry.get('itunes:episode', None)
    if meta_entry:
        return float(meta_entry)

    title = entry['title']
    hardcode = wcl_lookup.get(title, None)
    if hardcode:
        return float(hardcode)

    as_split = re.split(r'[-‒–—:]', title)
    deprefixed = as_split[0].lower().removeprefix('episode').strip()
    if deprefixed.isdigit():
        return float(deprefixed)

    return None


def episode_number_tgn(entry):
    tgn_lookup = {
        "Drafting High-End Watches With A Sense Of Adventure – A TGN Special With Collective Horology": 214.5,
        "The Grey NATO – 206 Re-Reupload – New Watches! Pelagos 39, Diver's Sixty-Five 12H, And The Steel Doxa Army": 206.5,
        "The Grey NATO – A Week Off (And A Request!)": 160.5,
        "Depth Charge - The Original Soundtrack by Oran Chan": 143.5,
        "The Grey Nato Ep 25  - Dream Watches 2017": 25,
        "The Grey Nato - Question & Answer #1": 20.5,
        "TGN Chats - Merlin Schwertner (Nomos Watches) And Jason Gallop (Roldorf & Co)": 16.5,
        "TGN Chats - Chase Fancher :: Oak & Oscar": 14.5,
        "Drafting Our Favorite Watches Of The 1970s – A TGN Special With Collective Horology": 260.5,
        "The Grey NATO – The Ineos Grenadier Minisode With Thomas Holland": 282.5,
        "Out Of Office – Back August 22nd": 295.5,
        "The Grey NATO – 300!": 300
    }
    title = entry['title']

    hardcode = tgn_lookup.get(title, None)
    if hardcode:
        return float(hardcode)

    as_split = re.split(r'[-‒–—]', title)
    if len(as_split) < 2:
        return None

    second = as_split[1].strip()
    if second.isdigit():
        return float(second)
    elif second.lower().startswith('ep'):
        sub_split = second.split()
        if len(sub_split) == 2 and sub_split[1].isdigit():
            return float(sub_split[1])

    return None


# NEW CHRONOLOGICAL NUMBERING

def get_chronological_numbering(feed_path: Path):
    """
    Parse RSS feed and assign episode numbers chronologically (oldest = 1, newest = N).
    Returns dict mapping title to episode number.
    """
    tree = ET.parse(feed_path)
    root = tree.getroot()
    items = root.findall('.//item')

    episodes_data = []
    for item in items:
        pubdate_elem = item.find('pubDate')
        title_elem = item.find('title')

        if pubdate_elem is None or title_elem is None:
            continue

        pubdate = parse_pubdate(pubdate_elem.text)
        episodes_data.append({
            'title': title_elem.text,
            'pubdate': pubdate,
        })

    # Sort by pubdate (oldest first)
    episodes_data.sort(key=lambda x: x['pubdate'])

    # Assign sequential numbers
    numbering = {}
    for position, ep_data in enumerate(episodes_data):
        numbering[ep_data['title']] = position + 1

    return numbering


def compare_podcast(name: str, feed_path: Path, old_func):
    """Compare old vs new numbering for a podcast."""
    log.info(f"\n{'='*80}")
    log.info(f"Analyzing {name}")
    log.info(f"{'='*80}")

    # Get old numbering using xmltodict (like process.py does)
    with open(feed_path, 'r') as f:
        entries = xmltodict.parse(f.read())

    old_numbering = {}
    missing_count = 0
    for entry in entries['rss']['channel']['item']:
        title = entry['title']
        number = old_func(entry)
        if number is None:
            missing_count += 1
            log.warning(f"  OLD method could not parse: {title}")
        else:
            old_numbering[title] = number

    # Get new chronological numbering
    new_numbering = get_chronological_numbering(feed_path)

    log.info(f"\nTotal episodes: {len(entries['rss']['channel']['item'])}")
    log.info(f"Old method missing: {missing_count}")
    log.info(f"New method assigns: {len(new_numbering)}")

    # Compare
    differences = []
    for title, new_num in new_numbering.items():
        old_num = old_numbering.get(title)
        if old_num is None:
            differences.append((title, None, new_num, "MISSING IN OLD"))
        elif old_num != new_num:
            differences.append((title, old_num, new_num, "DIFFERENT"))

    # Also check for episodes in old but not in new
    for title, old_num in old_numbering.items():
        if title not in new_numbering:
            differences.append((title, old_num, None, "MISSING IN NEW"))

    if differences:
        log.warning(f"\nFound {len(differences)} differences:")
        for title, old_num, new_num, reason in differences[:20]:  # Show first 20
            log.warning(f"  {reason}: {title[:60]}")
            log.warning(f"    Old: {old_num}, New: {new_num}")
        if len(differences) > 20:
            log.warning(f"  ... and {len(differences) - 20} more differences")
    else:
        log.info(f"\n✓ No differences found! Old and new numbering match perfectly.")

    return len(differences)


def main():
    log.remove()
    log.add(lambda msg: print(msg, end=''), level="INFO")

    test_dir = Path('test_feeds')

    total_diffs = 0

    total_diffs += compare_podcast(
        'TGN',
        test_dir / 'tgn.rss',
        episode_number_tgn
    )

    total_diffs += compare_podcast(
        'WCL',
        test_dir / 'wcl.rss',
        episode_number_wcl
    )

    total_diffs += compare_podcast(
        'Hodinkee',
        test_dir / 'hodinkee.rss',
        episode_number_hodinkee
    )

    log.info(f"\n{'='*80}")
    log.info(f"SUMMARY")
    log.info(f"{'='*80}")
    log.info(f"Total differences across all podcasts: {total_diffs}")

    if total_diffs == 0:
        log.info("✓ Safe to switch to chronological numbering!")
    else:
        log.warning("⚠ Review differences before switching numbering schemes")


if __name__ == "__main__":
    main()
