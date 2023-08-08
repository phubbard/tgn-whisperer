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
    subtitle: str = None
    mp3_url: str = None
    episode_url: str = None
    directory: str = None
    pub_date: str = None
    pub_directory: str = None


def episode_number(entry, index_notfound) -> tuple:
    try:
        number = entry['itunes:episode']
        return number, index_notfound
    except KeyError:
        log.warning(f'No episode number found for {entry["title"]}, trying regex...')
        groups = title_matcher.search(entry['title'])
        if not groups:
            log.info(f'Unable to parse episode ID from title {entry["title"]}, using {index_notfound}')

            return index_notfound, index_notfound + 1
        log.info(f'Found episode ID {groups[0]} from title')
        return int(groups[0]), index_notfound


def top_level_process(ep_dict):
    # Erase old episodes.md
    mkdocs_dir = '40and20/docs'
    ep_page = Path(mkdocs_dir, 'episodes.md')

    ep_page.unlink(missing_ok=True)

    rc = 0
    index_notfound = 2000
    for entry in ep_dict['rss']['channel']['item']:
        episode = Episode()
        episode.episode_url = entry['link']
        episode.mp3_url = entry['enclosure']['@url']
        episode.title = entry['title']
        episode.subtitle = entry['itunes:subtitle']
        episode.pub_date = entry['pubDate']
        episode.directory = Path('40and20episodes', str(episode.number)).absolute()
        episode.pub_directory = Path(mkdocs_dir, 'episodes', str(episode.number)).absolute()
        episode.number, index_notfound = episode_number(entry, index_notfound)

        if not episode.directory.exists():
            log.debug(f'Creating {episode.directory}')
            episode.directory.mkdir(parents=True)
        else:
            log.debug(f'{episode.directory} already exists')

        if not Path(episode.pub_directory).exists():
            log.debug(f'Creating {episode.pub_directory}')
            Path(episode.pub_directory).mkdir(parents=True)
        else:
            log.debug(f'{episode.pub_directory} already exists')

        # Path isn't serializable, but posix is
        episode.directory = episode.directory.as_posix()
        episode.pub_directory = episode.pub_directory.as_posix()

        log.debug(f'Saving json to {episode.directory}')
        json.dump(asdict(episode), open(Path(episode.directory, 'episode.json'), 'w'), indent=4)

        # Append markdown file link into nav page
        with open(ep_page, 'a') as yindex:
             yindex.write(f'- [{episode.title}]({"episodes/" + str(episode.number) + "/episode.md"}) {episode.pub_date}\n')
        rc += 1

    if rc == len(ep_dict['rss']['channel']['item']):
        log.info(f'Processed all {rc} episodes')
    else:
        log.warning(f'Processed {rc} episodes, {len(ep_dict["rss"]["channel"]["item"])} expected')


if __name__ == '__main__':
    filename = 'feed.xml'
    log.info(f'Reading {filename}...')
    fd = open(filename, 'r').read()
    log.info('Parsing')
    data = xmltodict.parse(fd)
    log.info('Processing')
    top_level_process(data)
