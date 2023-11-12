#!/usr/bin/env python3

# pfh 11/4/2023, rewrite as no-Makefiles, Python-only

from functools import wraps
import logging
import os
from pathlib import Path
import shutil
import sys

from invoke import task
from requests_cache import CachedSession
import xmltodict

logging.basicConfig(level=logging.DEBUG, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()

session: CachedSession = CachedSession('whisperer-cache', cache_control=True)


def src_newer(src: Path, dest: Path) -> bool:
    log.debug("Checking file modification timestamps")
    ts1 = os.stat(src)
    ts2 = os.stat(dest)
    if ts2.st_mtime >= ts1.st_mtime:
        log.debug(f"dest {dest} is newer than {src} by {ts2.st_mtime - ts1.st_mtime}")
        return False
    log.debug(f"source {src} is newer than {dest}")
    return True


def cp_task(src: Path, dest: Path):
    if not src_newer(src, dest):
        log.debug("skipping copy")
        return

    log.debug(f"starting copy of {src} to {dest}")
    shutil.copy(src, dest)
    log.debug("copy done")


def url_to_file(url: str, file: Path, overwrite=False):
    if not overwrite:
        if file.exists():
            log.debug(f"Skipping download of {url} since destination {file} exists")
            return
    rc = session.get(url)
    # TODO handle 429s
    if not rc.ok:
        log.error(f'Error retrieving {url}. {rc.status_code=} {rc.reason=}')
        return rc.status_code

    with open(file, 'w') as fw:
        fw.write(rc.content)
        log.info(f"Saved {url} to {file}")
        return 200


@task(help={'url': 'URL of the podcast RSS feed'})
def get_rss(url: str) -> list:
    # grab the RSS, parse into python array of dicts
    return []


@task()
def process_rss(entries: list) -> list:
    # for each episode/entry:
    #   create dest directory eg podcasts/tgn/123.0
    #   write episode.json
    #   write octoai.json
    return []


@task()
def write_episodes_md(dest_filename: Path, entries: list) -> None:
    # Given a path and list of episodes, write out the top-level episodes.md
    # used by mkdocs to build the website
    pass


@task()
def download_mp3(url: str, dest_filename: Path) -> None:
    # requests DL, using session cache, throw error if needed
    pass


@task()
def call_speech_to_text(url: str, payload: dict, dest_filename: Path) -> Path:
    # REST call to WhisperX to transcribe the episode. Returns the path of the transcript.json
    return Path('/')


@task()
def download_html(url: str, dest_filename: Path) -> None:
    # Local mirror, urls rewritten - not sure if Requests can handle this or we need wget/curl
    pass


@task()
def speaker_attribution(podcast_name: str, utterances: list) -> list:
    # Heuristics and/or ChatGPT to convert SPEAKER_OO into 'Jason Heaton'
    return []

@task()
def extract_text(dest_filename: Path, episode_transcript: Path) -> None:
    # Save transcript raw text into separate file
    pass


@task()
def create_episode_markdown(dest_filename: Path, transcript: Path, episode_file: Path) -> None:
    # Stitch together the episode info and the podcast transcript into a single markdown file
    pass

@task()
def call_mkdocs(work_dir: Path) -> None:
    # change dir and call mkdocs build, throw exception if needed
    pass

@task()
def call_rsync(work_dir: Path, dest_url: str) -> None:
    # call rsync to copy files across, throw exception if needed
    pass

@task()
def send_emails(emails: list) -> None:
    # if new episodes, notify listeners
    pass


