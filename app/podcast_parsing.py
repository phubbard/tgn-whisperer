# Routines to handle the vagaries of parsing different podcasts into a data structure.
# In the first two, I've seen missing episode numbers, sometimes missing URLs, missing subtitles, CDATA in
# text fields, its a mess.
from dataclasses import dataclass, asdict
import re

# Common code - parse episode number from title and URL out a random string. TGN especially.


title_re = r'(\d+)'
title_matcher = re.compile(title_re)

# Via, of course, https://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url#3809435
url_rs = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
url_matcher = re.compile(url_rs)

# TODO
@dataclass
class EpisodeLink:
    description: str
    url: str


# Data structure for a single episode. Will be saved as JSON into the episodes' directory and used by Make.
@dataclass
class Episode:
    number: int = 0
    title: str = None
    subtitle: str = None
    mp3_url: str = None
    episode_url: str = None
    directory: str = None
    pub_date: str = None
    links: list[EpisodeLink] = None

####################
# 40 and 20 routines


def episode_number(entry, index_notfound) -> tuple:
    if 'itunes:episode' in entry:
        number = entry['itunes:episode']
        return number, index_notfound

    log.warning(f'No episode number found for {entry["title"]}, trying regex...')
    groups = title_matcher.search(entry['title'])
    if groups:
        log.info(f'Found episode ID {groups[0]} from title')
        return int(groups[0]), index_notfound

    log.info(f'Unable to parse episode ID from title {entry["title"]}, trying TGN special list')
    rc = match_missing_numbers(entry['title'])
    if not rc:
        log.warning(f'Unable to determine number, using notfound index {index_notfound}')
        return index_notfound, index_notfound + 1


def episode_url(entry, default_url='https://thegreynato.com/'):
    if 'link' in entry:
        return entry['link']

    log.debug(f'No proper URL found, searching description')
    groups = url_matcher.search(entry['description'])
    if groups:
        log.debug(f'Found {groups[0]}, {len(groups)=}')
        return groups[0]
    log.warning(f'No episode URL found, returning {default_url=}')
    return default_url


def match_missing_numbers(title) -> int:
    # There's a half-dozen of malformed episode titles; this is a workaround. There's no gap in the episode numbers,
    # so I chose to do this. Currently at episode 256, so this should work for a decade or so.
    eps = {
        'TGN Chats - Chase Fancher :: Oak & Oscar': 2000,
        'TGN Chats - Merlin Schwertner (Nomos Watches) And Jason Gallop (Roldorf & Co)': 2001,
        'Drafting High-End Watches With A Sense Of Adventure – A TGN Special With Collective Horology': 2002,
        'The Grey NATO – A Week Off (And A Request!)': 2003,
        'Depth Charge - The Original Soundtrack by Oran Chan': 2004,
    }
    if title in eps.keys():
        return eps[title]
    log.error(f'Unable to find missing-number episode in list! {title=}')
    return None
