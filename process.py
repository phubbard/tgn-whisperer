from dataclasses import dataclass, asdict
import logging
import json
import re
import time
from pathlib import Path

import xmltodict
from bs4 import BeautifulSoup

# Log to a file instead of stdout. Config from
# https://stackoverflow.com/questions/6386698/how-to-write-to-a-file-using-the-logging-python-module#6386990
# logging.basicConfig(filename='logfile.txt', filemode='a',
#                     level=logging.DEBUG,
#                     format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
logging.basicConfig(level=logging.INFO,
                    format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()


title_re = r'(\d+)'
title_matcher = re.compile(title_re)
# Via, of course, https://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url#3809435
url_rs = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
url_matcher = re.compile(url_rs)


@dataclass
class Episode:
    number: int = 0
    title: str = None
    mp3_url: str = None
    episode_url: str = None
    directory: str = None
    pub_date: str = None


def title_to_ep_num(title: str) -> int:
    # Episode number is in the title, format like "Episode 123 : Title"
    groups = title_matcher.search(title)
    if not groups:
        log.info(f'Unable to parse episode ID from title {title}')
        return match_missing_numbers(title)
    return int(groups[0])


def desc_to_url(desc: str):
    # Episode URL is in the episode description
    groups = url_matcher.search(desc)
    if not groups:
        log.warning(f'Unable to parse URL from description {desc}')
        return 'https://thegreynato.com/'
    return groups[0]


def directory_path(mp3_url: str) -> Path:
    # Given an mp3 url, return the corresponding directory within the episodes/ directory.
    # Take the mp3 url, grab the last bits
    tokens = mp3_url.split('/')
    element = tokens[-1]
    if element.endswith('mp3'):
        element = element[:-len('.mp3')]
        return Path(f'episodes/{element}')
    raise ValueError(f'Unable to find mp3 substring in {mp3_url=}')


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
    return 0


def top_level_process(ep_dict):
    # Erase old episodes.md
    ep_page = Path('TheGreyNATO/docs/episodes.md')
    ep_page.unlink(missing_ok=True)

    rc = 0
    for entry in ep_dict['rss']['channel']['item']:
        episode = Episode()
        episode.episode_url = desc_to_url(entry['description'])
        episode.mp3_url = entry['enclosure']['@url']
        episode.number = title_to_ep_num(entry['title'])
        episode.title = entry['title']
        episode.pub_date = entry['pubDate']
        episode.directory = directory_path(episode.mp3_url)

        if not episode.directory.exists():
            log.debug(f'Creating {episode.directory}')
            episode.directory.mkdir(parents=True)
        else:
            log.debug(f'{episode.directory} already exists')

        # Convert to string for serialization
        episode.directory = episode.directory.as_posix()
        log.debug(f'Saving json to {episode.directory}')
        json.dump(asdict(episode), open(Path(episode.directory, 'episode.json'), 'w'), indent=4)

        # TODO
        # append markdown file link into nav page
        with open('TheGreyNATO/docs/episodes.md', 'a') as yindex:
             yindex.write(f'- [{episode.title}]({episode.directory + "/episode.md"}) {episode.pub_date}\n')
        rc += 1

    if rc == len(ep_dict['rss']['channel']['item']):
        log.info(f'Processed all {rc} episodes')
    else:
        log.warning(f'Processed {rc} episodes, {len(ep_dict["rss"]["channel"]["item"])} expected')


if __name__ == '__main__':
    filename = '2049759.rss'
    log.info(f'Reading {filename}...')
    fd = open(filename, 'r').read()
    log.info('Parsing')
    data = xmltodict.parse(fd)
    log.info('Processing')
    top_level_process(data)
