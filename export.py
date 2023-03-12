import logging
import json
import re
import time

import requests
from tqdm import tqdm
import xmltodict
from bs4 import BeautifulSoup

# Now that we have tqdm, lets log to a file instead of stdout. Config from
# https://stackoverflow.com/questions/6386698/how-to-write-to-a-file-using-the-logging-python-module#6386990
logging.basicConfig(filename='logfile.txt', filemode='a',
                    level=logging.DEBUG,
                    format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()


title_re = r'(\d+)'
title_matcher = re.compile(title_re)
# Via, of course, https://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url#3809435
url_rs = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
url_matcher = re.compile(url_rs)


def title_to_ep_num(title: str) -> int:
    groups = title_matcher.search(title)
    if not groups:
        log.error(f'Unable to parse episode ID from title {title}')
        return None
    return int(groups[0])


def title_to_fulltext(mp3url: str) -> str:
    # Given a title, load the fulltext from the corresponding file.
    # Take the mp3 url, grab the last bits
    tokens = mp3url.split('/')
    element = tokens[-1]
    if element.endswith('mp3'):
        element = element[:-len('.mp3')] + '.txt'
        with open(f'tgn/{element}', 'r') as fh:
            return fh.read()
    log.error(f'Unable to find mp3 substring in {mp3url=}')


def desc_to_url(desc: str):
    groups = url_matcher.search(desc)
    if not groups:
        log.error(f'Unable to parse URL from description {desc}')
        return None
    return groups[0]


def get_episode_urls(ep_page: str) -> list:
    # TODO filter out same-site links
    if not ep_page:
        return []
    log.debug(f'Fetching episode page {ep_page=}')
    try:
        r = requests.get(ep_page)
        if r.status_code != 200:
            log.error(f'Error {r.status_code} fetching {ep_page=}')
            return []
    except:
        log.error(f'Error pulling episode page {ep_page}')
        return []
    try:
        rc = []
        log.debug('Parsing URLs from page')
        soup = BeautifulSoup(r.content, 'html.parser')
        for link in soup.find_all('a'):
            rc.append(link.get('href'))
    except:
        log.warning(f'Ignoring all errors retrieving {ep_page}')

    log.debug(f'Found {len(rc)} URLs in {ep_page}')
    return rc


def make_slug_html(links, title, url) -> str:
    # FIXME this is terrible. Jinja2?
    rc = f'<html><title>{title}</title><body><a href="{url}">{url}</a> <h3>Links</h3><ol>'
    for link in links:
        rc += f'<li><a href="{link}">{link}</a></li>'
    rc += '</ol></body></html>'
    return rc


def filter_list(ep_dict):
    rc_array = []
    id = 0
    for entry in tqdm(ep_dict['rss']['channel']['item']):
        ep_url = desc_to_url(entry['description'])
        mp3url = entry['enclosure']['@url']
        item = {
            'id': id,
            'ep_id': title_to_ep_num(entry["itunes:title"]),
            'mp3url': mp3url,
            'ep_url': ep_url,
            'slug': make_slug_html(get_episode_urls(ep_url), entry['itunes:title'], ep_url),
            'pub_date': entry['pubDate'],
            'fulltext': title_to_fulltext(mp3url),
        }
        rc_array.append(item)
        id += 1
        # bit.ly and others have secret rate limits. this slows us down enough. Not sure if less would work.
        time.sleep(5)
    return rc_array


def process(filename='2049759.rss'):
    log.info(f'Reading {filename}...')
    fd = open(filename, 'r').read()
    log.info('Parsing')
    data = xmltodict.parse(fd)
    log.info('Processing')
    out = filter_list(data)
    output = open('data.json', 'w')
    log.info('Saving')
    json.dump(out, output)


if __name__ == '__main__':
    process()
