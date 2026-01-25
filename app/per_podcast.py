# Routines that handle imperfect podcast RSS feeds. Look here first for bugs.

import json
import re

from prefect import get_run_logger

from datastructures import Podcast
from configuration import url_matcher


def episode_number(pod: Podcast, entry: dict) -> float:
    # sorry Brad
    match pod.name:
        case 'tgn':
            return episode_number_tgn(entry)
        case 'wcl':
            return episode_number_wcl(entry)
        case _:
            raise ValueError(f"Unknown podcast {pod.name}")


def episode_number_wcl(entry):
    # Episode logic for WCL (40 and 20). Generally a clean and correct RSS, so fewer workarounds.
    log = get_run_logger()
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

    log.warning(f"FAIL: -> {title}")
    return None


def episode_number_tgn(entry):
    # Episode number logic for TGN. Early feed was super crufty, so several workarounds and special cases.
    log = get_run_logger()
    tgn_lookup = {
        "Drafting High-End Watches With A Sense Of Adventure – A TGN Special With Collective Horology": 214.5,
        "The Grey NATO – 206 Re-Reupload – New Watches! Pelagos 39, Diver's Sixty-Five 12H, And The Steel Doxa Army": 206.5,
        "The Grey NATO – A Week Off (And A Request!)": 160.5,
        "Depth Charge - The Original Soundtrack by Oran Chan"
        "": 143.5,
        "The Grey Nato Ep 25  - Dream Watches 2017": 25,
        "The Grey Nato - Question & Answer #1": 20.5,
        "TGN Chats - Merlin Schwertner (Nomos Watches) And Jason Gallop (Roldorf & Co)": 16.5,
        "TGN Chats - Chase Fancher :: Oak & Oscar": 14.5,
        "Drafting Our Favorite Watches Of The 1970s – A TGN Special With Collective Horology": 260.5
    }
    title = entry['title']

    hardcode = tgn_lookup.get(title, None)
    if hardcode:
        return float(hardcode)

    as_split = re.split(r'[-‒–—]', title)
    if len(as_split) < 2:
        log.warning(f"FAIL: -> {title}")
        return None

    second = as_split[1].strip()
    if second.isdigit():
        return float(second)
    elif second.lower().startswith('ep'):
        sub_split = second.split()
        if len(sub_split) == 2 and sub_split[1].isdigit():
            return float(sub_split[1])

    log.warning(f"FAIL: -> {title}")
    return None


def episode_url(entry, default_url='https://thegreynato.com/'):
    # Per-episode URLs are also important; we try to download a web page snapshot at runtime.
    # Priority is link in RSS, regex from episode description, and lastly we return the default.
    log = get_run_logger()
    if 'link' in entry:
        return entry['link']

    log.debug(f'No proper URL found, searching description')
    groups = url_matcher.search(entry['description'])
    if groups:
        log.debug(f'Found {groups[0]}')
        return groups[0]
    log.warning(f'No episode URL found, returning {default_url=} for {entry["title"]}')
    return default_url


def unwrap_bitly(url: str) -> str:
    # Early TGN used bit.ly, which is fucking horrid. Let's get rid of them.
    log = get_run_logger()
    rc = url.lower().find('bit.ly')
    if rc < 0:
        return url
    # Do we know it?
    lookup_map = json.load(open('./app/bitly.json', 'r'))
    if url in lookup_map.keys():
        return lookup_map[url]
    err_str = f"{url=} not found in bitly.json! Re-run unwrap-bitly with this URL."
    log.error(err_str)
    raise ValueError(err_str)
    # return url
