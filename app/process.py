from dataclasses import asdict
import json
import logging
from pathlib import Path
import sys

import requests
import xmltodict

from app import Episode, Podcast
from podcast_parsing import episode_number, episode_url


logging.basicConfig(level=logging.INFO, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()

tgn = Podcast('tgn', 254, 'https://feeds.buzzsprout.com/2049759.rss')
wcl = Podcast('wcl', 254, 'https://feed.podbean.com/the40and20podcast/feed.xml')
# Iterable to loop over
podcasts = [tgn, wcl]


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
        mkdocs_mainpage = Path(basedir, 'episodes.md')
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
