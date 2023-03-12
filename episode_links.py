import logging
import re
import sys

import xmltodict

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


def desc_to_url(desc: str):
    groups = url_matcher.search(desc)
    if not groups:
        log.error(f'Unable to parse URL from description {desc}')
        return None
    return groups[0]


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
        if url:
            print(url)

