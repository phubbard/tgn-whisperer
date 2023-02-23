import logging
import json
import re

import xmltodict

logging.basicConfig(level=logging.INFO, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
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


def desc_to_url(desc: str):
    groups = url_matcher.search(desc)
    if not groups:
        log.error(f'Unable to parse URL from description {desc}')
        return None
    return groups[0]


def filter_list(ep_dict):
    rc_array = []
    for entry in ep_dict['rss']['channel']['item']:
        id = title_to_ep_num(entry["itunes:title"])
        mp3url = entry['enclosure']['@url']
        url = desc_to_url(entry['description'])
        slug = entry['itunes:title']  # TODO split off prefix and ep#
        pubdate = entry['pubDate']

        rc = {}
        rc['id'] = id
        rc['url'] = url
        rc['mp3url'] = mp3url
        rc['slug'] = slug
        rc['pubdate'] = pubdate
        rc_array.append(rc)
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
