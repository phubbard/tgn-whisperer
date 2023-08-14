from dataclasses import asdict
import logging
import json
from pathlib import Path
import sys

import requests
import xmltodict

from config import podcasts
from podcast_parsing import episode_number, episode_url, Episode

logging.basicConfig(level=logging.INFO, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()


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
        log.info(f"Found {ep_count} episodes in {podcast}")
        for entry in entries:
            episode = Episode()
            episode.number, index_notfound = episode_number(entry, index_notfound)
            if episode.number in seen_episodes:
                log.error(f"FATAL: Duplicate episode number {episode.number} in {podcast}, stopping")
                sys.exit(1)
            seen_episodes.add(episode.number)
            episode.episode_url = episode_url(entry)
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
                ep_index.write(f"- [{episode.title}]({str(episode.number)}/episode.md) {episode.pub_date}")
            count += 1
        # Done with this podcast - check episode count
        if count == ep_count:
            log.info(f"Processed all {ep_count} episodes in {podcast.name}")
        else:
            log.warning(f"Processed {count} episodes out of {ep_count} possible")


if __name__ == '__main__':
    process_all_podcasts()
