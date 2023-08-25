from dataclasses import asdict, dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import re

import requests
import xmltodict


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
    site_directory: str = None
    links: list[EpisodeLink] = None


@dataclass
class Podcast:
    name: str  # Unix style, short lowercase, used as a parent directory1
    last_notified: int  # TODO
    rss_url: str


logging.basicConfig(level=logging.INFO, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()

tgn = Podcast('tgn', 254, 'https://feeds.buzzsprout.com/2049759.rss')
wcl = Podcast('wcl', 254, 'https://feed.podbean.com/the40and20podcast/feed.xml')
# Iterable to loop over
podcasts = [tgn, wcl]


# Regex to pull the first number from a title - podcast number, in this case
title_re = r'(\d+)'
title_matcher = re.compile(title_re)

# Grab any valid URL. Super complex, so classic cut and paste coding.
# Via, of course, https://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url#3809435
url_rs = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
url_matcher = re.compile(url_rs)


def episode_number(entry, index_notfound) -> tuple:
    # We try four ways to get the episode number, since its our primary key for everything.
    # Metadata is best, title string second, special-case list and lastly we create a list.
    if 'itunes:episode' in entry:
        number = entry['itunes:episode']
        return number, index_notfound

    log.debug(f'Unable to parse episode ID from title {entry["title"]}, trying TGN special list')
    rc = match_missing_numbers(entry['title'])
    if rc:
        log.info(f"Found in TGN exception list {rc=}")
        return rc, index_notfound

    log.debug(f'No exception number found for {entry["title"]}, trying regex...')
    groups = title_matcher.search(entry['title'])
    if groups:
        log.debug(f'Found episode ID {groups[0]} from title')
        return int(groups[0]), index_notfound

    log.warning(f'Unable to determine number, using notfound index {index_notfound} for {entry["title"]}')
    return index_notfound, index_notfound + 1


def episode_url(entry, default_url='https://thegreynato.com/'):
    if 'link' in entry:
        return entry['link']

    log.debug(f'No proper URL found, searching description')
    groups = url_matcher.search(entry['description'])
    if groups:
        log.debug(f'Found {groups[0]}')
        return groups[0]
    log.warning(f'No episode URL found, returning {default_url=} for {entry["title"]}')
    return default_url


def match_missing_numbers(title) -> int:
    # There's a half-dozen of malformed episode titles; this is a workaround. There's no gap in the episode numbers,
    # so I chose to do this. Currently at episode 256, so this should work for a decade or so.
    # TODO - move this into an exceptions.json like the bitly workaround.b
    eps = {
        'TGN Chats - Chase Fancher :: Oak & Oscar': 2000,
        'TGN Chats - Merlin Schwertner (Nomos Watches) And Jason Gallop (Roldorf & Co)': 2001,
        'Drafting High-End Watches With A Sense Of Adventure – A TGN Special With Collective Horology': 2002,
        'The Grey NATO – A Week Off (And A Request!)': 2003,
        'Depth Charge - The Original Soundtrack by Oran Chan': 2004,
        'The Grey Nato - Question & Answer #1': 2005,
    }
    if title in eps.keys():
        return eps[title]
    log.debug(f'Unable to find missing-number episode in list! {title=}')
    return None


def unwrap_bitly(url: str) -> str:
    # Early TGN used bit.ly, which is fucking horrid. Let's get rid of them.
    rc = url.lower().find('bit.ly')
    if rc < 0:
        return url
    # Do we know it?
    lookup_map = json.load(open('./app/bitly.json', 'r'))
    if url in lookup_map.keys():
        return lookup_map[url]
    log.warning(f"{url=} not found in bitly.json! Re-run unwrap-bitly with this URL.")
    return url


def process_all_podcasts():
    for podcast in podcasts:
        count = 0
        index_notfound = 2100
        # Keep a Set of episode numbers to bug-check the unnumbered episode logic
        seen_episodes = set()

        log.info(f'Processing {podcast}')
        basedir = Path('podcasts', podcast.name)
        mkdocs_mainpage = Path('sites', podcast.name, 'docs', 'episodes.md')
        log.info(f'Removing {mkdocs_mainpage}')
        mkdocs_mainpage.unlink(missing_ok=True)

        log.info(f'Fetching RSS feed {podcast.rss_url}')
        rc = requests.get(podcast.rss_url)
        if not rc.ok:
            log.error(f'Error pulling RSS feed, skipping {podcast}. {rc.status_code=} {rc.reason=}')
            continue

        log.debug('Parsing XML')
        entries = xmltodict.parse(rc.text)
        ep_count = len(entries['rss']['channel']['item'])
        mkdocs_mainpage.write_text(f"### Page updated {datetime.now().astimezone().isoformat()} - {ep_count} episodes\n")
        log.info(f"Found {ep_count} episodes in {podcast.name}")
        for entry in entries['rss']['channel']['item']:
            episode = Episode()
            episode.number, index_notfound = episode_number(entry, index_notfound)
            if episode.number in seen_episodes:
                # TGN 206 was re-uploaded. FML.
                log.warning(f"Ignoring duplicate {episode.number} in {podcast.name}")
                # log.error(f"FATAL: Duplicate episode number {episode.number} in {podcast}, stopping")
                continue
            seen_episodes.add(episode.number)
            episode.episode_url = unwrap_bitly(episode_url(entry))
            if 'subtitle' in entry:
                episode.subtitle = entry['subtitle']
            else:
                episode.subtitle = ''
            episode.mp3_url = entry['enclosure']['@url']
            episode.title = entry['title']
            episode.pub_date = entry['pubDate']

            # Filesystem
            episode.directory = Path(basedir, str(episode.number)).absolute()
            if not episode.directory.exists():
                log.debug(f'Creating {episode.directory}')
                episode.directory.mkdir(parents=True)
            # Rewrite as POSIX path, as basic paths can't serialize to JSON
            episode.directory = episode.directory.as_posix()

            # mkdocs director¥ for this episode - sites/tgn/docs/40 for example
            episode.site_directory = Path('sites', podcast.name, 'docs', str(episode.number)).absolute()
            if not episode.site_directory.exists():
                log.debug(f"Creating site directory {episode.site_directory}")
                episode.site_directory.mkdir(parents=True)
            episode.site_directory = episode.site_directory.as_posix()

            log.debug(f'Saving json to {episode.directory}')
            json.dump(asdict(episode), open(Path(episode.directory, 'episode.json'), 'w'))

            # Add this episode to the episode markdown page
            with open(mkdocs_mainpage, 'a') as ep_index:
                ep_index.write(f"- [{episode.title}]({str(episode.number)}/episode.md) {episode.pub_date}\n")
            count += 1
        # Done with this podcast - check episode count
        if count == ep_count:
            log.info(f"Processed all {ep_count} episodes in {podcast.name}")
        else:
            log.warning(f"Processed {count} episodes out of {ep_count} possible")


if __name__ == '__main__':
    process_all_podcasts()
