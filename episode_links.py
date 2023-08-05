#!/usr/bin/env python3
'''
Script to partially process the saved RSS XML. For each podcast episode,
output a curl command that will download and rewrite the episode page.
Doing it this way lets us use file-based builds (Make, that is) and avoids
being a bad netizen by hammering the server with requests.
Once they're saved into html files, we can iterate with BeautifulSoup and mkdocs.
'''
import logging
import re
import sys
from pathlib import Path

import xmltodict

# Log to a file instead of stdout. Config from
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


def desc_to_url(desc: str):
    groups = url_matcher.search(desc)
    if not groups:
        log.error(f'Unable to parse URL from description {desc}')
        return None
    return groups[0]



def url_to_filename(url: str, suffix='.html') -> Path:
    # Given an episode url, return the corresponding filename.
    # Take the mp3 url, grab the last bits
    tokens = url.split('/')
    if not tokens:
        log.warning(f'Unable to parse URL {url}')
        return None
    element = tokens[-1] + suffix
    return Path(f'tgn/{element}')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = '2049759.rss'

    log.info(f'Reading {filename}...')
    fd = open(filename, 'r').read()
    log.info('Parsing')
    data = xmltodict.parse(fd)
    log.info('Processing')
    for entry in data['rss']['channel']['item']:
        url = desc_to_url(entry['description'])
        if not url:
            log.warning('Skipping unparseable episode {entry["description"]')
            continue

        output_filename = url_to_filename(url)
        if url and output_filename:
            print(f'wget -O {output_filename} -P tgn -nc --wait=5 --random-wait --convert-links {url}')

