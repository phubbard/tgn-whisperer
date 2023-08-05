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
logging.basicConfig(level=logging.DEBUG,
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


def url_to_filename(mp3url: str, suffix='.txt') -> Path:
    # Given an mp3 url, return the corresponding filename.
    # Take the mp3 url, grab the last bits
    tokens = mp3url.split('/')
    element = tokens[-1]
    if element.endswith('mp3'):
        element = element[:-len('.mp3')] + suffix
        return Path(f'tgn/{element}')
    log.error(f'Unable to find mp3 substring in {mp3url=}')


def url_load_fulltext(mp3url: str) -> str:
    # Given an mp3 url, load the fulltext from the corresponding file.
    # Take the mp3 url, grab the last bits
    filename = url_to_filename(mp3url)
    if not filename:
        log.error(f'Unable to find mp3 substring in {mp3url=}')
        return None
    with open(filename, 'r') as fh:
        return fh.read()


def desc_to_url(desc: str):
    groups = url_matcher.search(desc)
    if not groups:
        log.error(f'Unable to parse URL from description {desc}')
        return None
    return groups[0]


def get_episode_urls(mp3url: str) -> list:
    # Load the page, parse out the URLs. Return a list of URLs.
    # TODO filter out same-site links
    html_filename = url_to_filename(mp3url, suffix='.html')
    if not html_filename:
        return []
    log.debug(f'Load episode page {html_filename}')
    try:
        fh = open(html_filename, 'r')
        html = fh.read()
        rc = []
        log.debug('Parsing URLs from page')
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a'):
            # TODO pull out the text between end of link and EOL
            rc.append(link.get('href'))
    except FileNotFoundError:
        log.error(f'Unable to find {html_filename}')
        return []

    log.debug(f'Found {len(rc)} URLs in {html_filename}')
    return rc


def top_level_process(ep_dict):
    rc = 0
    for entry in ep_dict['rss']['channel']['item']:
        ep_url = desc_to_url(entry['description'])
        mp3url = entry['enclosure']['@url']
        index = rc
        ep_id = title_to_ep_num(entry["itunes:title"])
        title = entry['itunes:title']
        links = get_episode_urls(mp3url)
        pub_date = entry['pubDate']
        fulltext = url_load_fulltext(mp3url)
        local_mdfile = url_to_filename(mp3url, suffix='.md')
        with open(local_mdfile, 'w') as fh:
            log.debug(f'Writing {local_mdfile}')
            data = f'''
            ---
            title: {title}
            date: {pub_date}
            ---
            # {title} published {pub_date} index {index}
            * [Episode page]({ep_url})
            * [Episode MP3]({mp3url})            
            '''
            if links:
                for link in links:
                    data += f'* [Link]({link})'
            else:
                data += 'No links found.'
            fh.write(data)

            # write out markdown file link into nav section of yaml file
            with open('TheGreyNATO/docs/episodes.md', 'a') as yindex:
                yindex.write(f'- [Episode {index}]({local_mdfile.name})\n')
        rc += 1


if __name__ == '__main__':
    filename = '2049759.rss'
    log.info(f'Reading {filename}...')
    fd = open(filename, 'r').read()
    log.info('Parsing')
    data = xmltodict.parse(fd)
    log.info('Processing')
    top_level_process(data)
