import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from email.message import EmailMessage
import json
import logging
from os import getenv
from pathlib import Path
import re
import smtplib

import requests
import xmltodict

system_admin = 'tgn-whisperer@phfactor.net'

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


OctoAI = {
    "url": "",
    "task": "transcribe",
    "diarize": True,
    "min_speakers": 2,
    "prompt": "The following is a conversation including James and Jason"  # FIXME for WCL
}


@dataclass
class Podcast:
    name: str  # Unix style, short lowercase, used as a parent directory
    rss_url: str
    emails: list[str]  # Who to email with new episodes
    doc_base_url: str  # Used to create URLs for emails
    number_extractor_function: object


class FastMailSMTP(smtplib.SMTP_SSL):
    """A wrapper for handling SMTP connections to FastMail.
    From https://alexwlchan.net/2016/python-smtplib-and-fastmail/
    with attachments code removed.
    """

    def __init__(self, username, password):
        super().__init__('mail.messagingengine.com', port=465)
        self.login(username, password)

    def send_fm_message(self, *,
                     from_addr,
                     to_addrs,
                     msg,
                     subject,
                     attachments=None):
        msg_root = EmailMessage()
        msg_root['Subject'] = subject
        msg_root['From'] = from_addr
        msg_root['To'] = ', '.join(to_addrs)

        self.sendmail(from_addr, to_addrs, msg_root.as_string())

logging.basicConfig(level=logging.INFO, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()


# Regex to pull the first number from a title - podcast number, in this case. Heuristic but works almost every time.
title_re = r'(\d+)'
title_matcher = re.compile(title_re)

# Grab any valid URL. Super complex, so classic cut and paste coding from StackOverflow.
# Of course. https://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url#3809435
url_rs = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
url_matcher = re.compile(url_rs)


wcl_lookup = {
    "Watch Clicker Mini Review - Nodus Sector Dive": 81.5,
    "Episode 36 GMT Watches": 36,
    }


def episode_number_wcl(entry):

    meta_entry = entry.get('itunes:episode', None)
    if meta_entry is not None: return float(meta_entry)

    title = entry['title']
    hardcode = wcl_lookup.get(title, None)
    if hardcode is not None: return float(hardcode)

    asSplit = re.split(r'[-‒–—\:]', title)

    deprefixed = asSplit[0].lower().removeprefix('episode').strip()
    if deprefixed.isdigit():
        return float(deprefixed)

    log.warning(f"FAIL: -> {title}")
    return None


tgn_lookup = {
    "Drafting High-End Watches With A Sense Of Adventure – A TGN Special With Collective Horology": 214.5,
    "The Grey NATO – 206 Re-Reupload – New Watches! Pelagos 39, Diver's Sixty-Five 12H, And The Steel Doxa Army": 206.5,
    "The Grey NATO – A Week Off (And A Request!)": 160.5,
    "Depth Charge - The Original Soundtrack by Oran Chan": 143.5,
    "The Grey Nato Ep 25  - Dream Watches 2017": 25,
    "The Grey Nato - Question & Answer #1": 20.5,
    "TGN Chats - Merlin Schwertner (Nomos Watches) And Jason Gallop (Roldorf & Co)": 16.5,
    "TGN Chats - Chase Fancher :: Oak & Oscar": 14.5,
    } 


def episode_number_tgn(entry):

    title = entry['title']

    hardcode = tgn_lookup.get(title, None)
    if hardcode is not None:
        return float(hardcode)

    asSplit = re.split(r'[-‒–—]', title)
    if len(asSplit) < 2:
        log.warning(f"FAIL: -> {title}")
        return None

    second = asSplit[1].strip()
    if second.isdigit():
        return float(second)
    elif second.lower().startswith('ep'):
        subsplit = second.split()
        if len(subsplit) == 2 and subsplit[1].isdigit():
            return float(subsplit[1])

    log.warning(f"FAIL: -> {title}")
    return None


# Iterable to loop over
podcasts = [
      Podcast('tgn', 'https://feeds.buzzsprout.com/2049759.rss',
              ['pfh@phfactor.net'], 'https://www.phfactor.net/tgn', episode_number_tgn),
      Podcast('wcl', 'https://feed.podbean.com/the40and20podcast/feed.xml',
              ['pfh@phfactor.net'], 'https://www.phfactor.net/wcl', episode_number_wcl),
      ]


def episode_url(entry, default_url='https://thegreynato.com/'):
    # Per-episode URLs are also important; we try to download a web page snapshot at runtime.
    # Priority is link in RSS, regex from episode description, and lastly we return the default.
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
    # There's a half-dozen malformed episode titles; this is a workaround. There's no gap in the episode numbers,
    # so I chose to do this. Currently at episode 256, so this should work for a decade or so.
    # TODO - move this into an exceptions.json like the bitly workaround.
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


def send_email(email_list, new_ep_list, base_url):
    # FastMail is the best.
    smtp_password = getenv('FASTMAIL_PASSWORD', None)
    if not smtp_password:
        log.error(f'FASTMAIL_PASSWORD not found in environment, cannot email')
        return
    if not new_ep_list:
        log.info('No new episodes to send in email')
        return
    subject = 'New episodes are available' if len(new_ep_list) > 1 else 'New episode available'

    payload = f'{len(new_ep_list)} episode(s): \n'
    for ep in new_ep_list:
        payload = payload + f"\n{base_url}/episodes/{ep['number']}"

    log.info(f'Emailing {email_list}')
    with FastMailSMTP(system_admin, smtp_password) as server:
        server.send_fm_message(from_addr=system_admin,
                               to_addrs=email_list,
                               msg=payload,
                               subject=subject)
        log.debug(payload)


def send_failure_alert(fail_message):
    # FastMail is the best.
    smtp_password = getenv('FASTMAIL_PASSWORD', None)
    if not smtp_password:
        log.error(f'FASTMAIL_PASSWORD not found in environment, cannot email')
        return

    with FastMailSMTP(system_admin, smtp_password) as server:
        server.send_fm_message(from_addr=system_admin,
                               to_addrs=system_admin,
                               msg=fail_message,
                               subject='Error in podcast processing')


def new_episodes(podcast_name: str, current_eps: list, update_saved: bool = True) -> list:
    # Given a list of new episodes (array of numbers), return a list of
    # episodes that were not in the saved list. As a side effect, update
    # the saved list
    filename = podcast_name + '-notified.json'
    try:
        old_list = json.load(open(filename, 'r'))
    except FileNotFoundError:
        log.warning('Saved file not found, starting over')
        old_list = []

    old_eps = set(old_list)
    current_eps = set(current_eps)
    all_eps = set(old_eps)
    all_eps.update(current_eps)
    new_eps = current_eps.difference(old_eps)
    new_count = len(new_eps)
    log.info(f'{new_count} new episodes found')
    if not new_count or not update_saved:
        return []

    log.info(f'Saving updated list of episodes in {podcast_name}')
    json.dump(list(all_eps), open(filename, 'w'))
    return list(new_eps)


def process_all_podcasts():
    for podcast in podcasts:
        count = 0

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

        fail_count = 0
        current_ep_numbers = set()

        # This loop is over all episodes in the current podcast
        for entry in entries['rss']['channel']['item']:

            be_number = podcast.number_extractor_function(entry)
            if be_number is None:
                fail_count += 1 # TODO

            episode = Episode()
            episode.number = be_number
            current_ep_numbers.add(be_number)
            episode.episode_url = unwrap_bitly(episode_url(entry))
            if 'subtitle' in entry:
                episode.subtitle = entry['subtitle']
            else:
                episode.subtitle = ''
            episode.mp3_url = entry['enclosure']['@url']
            episode.title = entry['title']
            episode.pub_date = entry['pubDate']

            OctoAI['url'] = episode.mp3_url

            # Filesystem
            episode.directory = Path(basedir, str(episode.number)).absolute()
            if not episode.directory.exists():
                log.debug(f'Creating {episode.directory}')
                episode.directory.mkdir(parents=True)
            # Rewrite as POSIX path, as basic paths can't serialize to JSON
            episode.directory = episode.directory.as_posix()

            # mkdocs directory for this episode - sites/tgn/docs/40 for example
            episode.site_directory = Path('sites', podcast.name, 'docs', str(episode.number)).absolute()
            if not episode.site_directory.exists():
                log.debug(f"Creating site directory {episode.site_directory}")
                episode.site_directory.mkdir(parents=True)
            episode.site_directory = episode.site_directory.as_posix()

            log.debug(f'Saving json to {episode.directory}')
            json.dump(asdict(episode), open(Path(episode.directory, 'episode.json'), 'w'))
            log.debug(f'Saving AI data to {episode.directory}')
            json.dump(OctoAI, open(Path(episode.directory, 'openai.json'), 'w'))

            # Add this episode to the episode markdown page
            with open(mkdocs_mainpage, 'a') as ep_index:
                ep_index.write(f"- [{episode.title}]({str(episode.number)}/episode.md) {episode.pub_date}\n")
            count += 1
        # Done with this podcast - check episode count

        if fail_count:
            fail_msg = f"UN-DISCERNIBLE EPISODES: -> {fail_count=}"
            send_failure_alert(fail_msg)
            sys.exit(1)

        if count == ep_count:
            log.info(f"Processed all {ep_count} episodes in {podcast.name}")
        else:
            log.warning(f"Processed {count} episodes out of {ep_count} possible")

        new_eps = new_episodes(podcast.name, list(current_ep_numbers))
        send_email(podcast.emails, new_eps, podcast.doc_base_url)

if __name__ == '__main__':
    process_all_podcasts()

