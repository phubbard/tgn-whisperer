#!/usr/bin/env python3

# pfh 11/12/2023 Try out workflow to orchestrate the tasks. After a brief eval, Precept
# looks preferable to Apache Airflow. Here we go!
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import shutil

import httpx
from prefect import flow, task, get_run_logger
import xmltodict
from configuration import PODCAST_ROOT, SITE_ROOT
from per_podcast import episode_number, episode_url, unwrap_bitly
from datastructures import Podcast, Episode, OctoAI
from pod_email import send_email, send_failure_alert

# log = get_run_logger()


@task(retries=2, name="URL to file downloader")
def url_to_file(url: str, file: Path, body: str = None, overwrite: bool=False) -> Path:
    # TODO handle JSON body for OctoAI call
    # TODO consider adding retry function https://docs.prefect.io/latest/concepts/tasks/
    # TODO handle 429s from OctoAI
    if not overwrite:
        if file.exists():
            log.debug(f"Skipping download of {url} since destination {file} exists")
            return file

    log.debug(f"Downloading {url} to {file}")
    rc = httpx.get(url)

    # If not 2xx, throw exception that should be handled by the task wrapper
    rc.raise_for_status()

    log.debug(f"Saving {url} to {file}")
    with open(file, 'w') as fw:
        fw.write(rc.text)
        log.info(f"Saved {url} to {file}")
        return file


@task
def new_episodes(podcast_name: str, current_eps: list, save_updated: bool = True) -> list:
    # Given a list of new episodes (array of numbers), return a list of
    # episodes that were not in the saved list. As an optional side effect, update
    # the saved list on disk.
    filename = podcast_name + '-notified.json'
    try:
        old_list = json.load(open(filename, 'r'))
    except FileNotFoundError:
        log.warning(f'Saved file {filename} not found, starting over')
        old_list = []

    old_eps = set(old_list)
    current_eps = set(current_eps)
    all_eps = set(old_eps)
    all_eps.update(current_eps)
    new_eps = current_eps.difference(old_eps)
    new_count = len(new_eps)
    if not new_count or not save_updated:
        log.debug(f'No new episodes found in {podcast_name}')
        return []

    log.info(f'{new_count} new episodes found in {podcast_name}')
    log.info(f'Saving updated list of episodes in {podcast_name} to {filename}')
    json.dump(list(all_eps), open(filename, 'w'))
    return list(new_eps)


@task(name="Parse RSS")
def rss_to_list(rss_file: Path, pod: {Podcast}) -> list:
    # Read RSS from local copy, return array of new episodes
    # FIXME need both full-list as well as new-episode lists
    with open(rss_file, 'r') as rh:
        entries = xmltodict.parse(rh.read())
        episode_count = len(entries['rss']['channel']['item'])
        log.info("Building episode list to check for new content")
        current_ep_numbers = set()
        fail_count = 0
        for entry in entries['rss']['channel']['item']:
            be_number = pod.number_extractor_function(entry)
            if be_number is None:
                fail_count += 1
            current_ep_numbers.add(be_number)

        if fail_count:
            fail_msg = f"{pod.name=} UN-DISCERNIBLE EPISODES: -> {fail_count=}"
            send_failure_alert(fail_msg)
            log.error(fail_msg)
            raise ValueError(fail_msg)

        new_eps = new_episodes(pod.name, list(current_ep_numbers))
        if not new_eps:
            log.info(f"No new episodes found in podcast {pod.name}.")
            return []
    return entries['rss']['channel']['item']


@task(name="Episode URL, numbering, directories")
def rss_cleanup(pod: Podcast, episodes: list) -> list:
    # Find, fix and renumber episodes. Find or guess per-episode URLs for later caching.
    # Pure function that processes and returns an array of Episodes
    # with another task that creates and populates the directories.

    # eg podcasts/tgn
    basedir = Path(PODCAST_ROOT, pod.name)

    rc = []
    for entry in episodes:
        episode = Episode()
        episode.number = episode_number(pod, entry)
        episode.episode_url = unwrap_bitly(episode_url(entry))
        if 'subtitle' in entry:
            episode.subtitle = entry['subtitle']
        else:
            episode.subtitle = ''
        episode.mp3_url = entry['enclosure']['@url']
        episode.title = entry['title']
        episode.pub_date = entry['pubDate']
        episode.octoai = OctoAI.copy()
        episode.octoai['url'] = episode.mp3_url
        # Rewrite as POSIX path, as basic Paths can't serialize to JSON
        episode.directory = Path(basedir, str(episode.number)).absolute().as_posix()
        # mkdocs directory for this episode - sites/tgn/docs/40.0 for example
        episode.site_directory = Path(SITE_ROOT, pod.name, 'docs', str(episode.number)).absolute().as_posix()

        rc.append(episode)

    return rc


@task(name="Populate episode directories with episode.json")
def populate_episode_dirs(episodes: list):
    for episode in episodes:
        json.dump(asdict(episode), open(Path(episode.directory, 'episode.json'), 'w'))


@task(name="Make podcast episode and mkdocs directories")
def make_podcast_dirs(pod: Podcast, episodes: list):
    for episode in episodes:
        m_dir = Path(episode.directory)
        s_dir = Path(episode.site_directory)
        if not m_dir.exists():
            log.debug(f'Creating {m_dir}')
            m_dir.mkdir(parents=True)
        if not s_dir.exists():
            log.debug(f'Creating {s_dir}')
            s_dir.mkdir(parents=True)



@task(name="Write mkdocs episodes.md")
def write_episodes_md(pod: Podcast, episodes: list):
    # NB Needs all episodes, not just the new ones, since we rewrite the index page.
    ep_count = len(episodes)
    basedir = Path(PODCAST_ROOT, pod.name)
    mkdocs_mainpage = Path(SITE_ROOT, pod.name, 'docs', 'episodes.md')
    log.debug(f'Removing {mkdocs_mainpage}')
    mkdocs_mainpage.unlink(missing_ok=True)

    ts = datetime.now().astimezone().isoformat()
    mkdocs_mainpage.write_text(f"### Page updated {ts} - {ep_count} episodes\n")
    log.info(f"Found {ep_count} episodes in {pod.name}")
    for episode in episodes:
        mkdocs_mainpage.write_text(f"- [{episode.title}]({str(episode.number)}/episode.md) {episode.pub_date}\n")


@task(name='Generate site with mkdocs')
def run_mkdocs(pod: Podcast):
    m_dir = Path(SITE_ROOT, pod.name)
    with os.chdir(m_dir):
        rc = os.system("mkdocs build")
        if rc != 0:
            err_str = f"{rc=} running mkdocs in {m_dir}"
            log.error(err_str)
            raise ValueError(err_str)


@task(name='Deploy with rsync')
def run_rsync(pod:Podcast):
    # eg sites/tgn/site
    r_dir = Path(SITE_ROOT, pod.name, 'site')
    with os.chdir(r_dir):
        exc_str = f"rsync -qrpgD --delete --force . usul:html/{pod.name}"
        rc = os.system(exc_str)
        if rc != 0:
            err_str = f"{rc=} running rsync in {r_dir} with {exc_str=}"
            log.error(err_str)
            raise ValueError(err_str)


@task(name='Send new-episode email')
def send_episode_email(pod: Podcast, new_eps: list):
    send_email(pod.emails, new_eps, pod.doc_base_url)


@task(name='Use LLM to attribute speakers')
def attribute_speakers(pod: Podcast, ep: Episode) -> dict:
    # TODO Stub, need to decide on an LLM and build it out
    log.warning(f"LLM not yet implemented, using manual attribution for {ep.title}")
    return {}