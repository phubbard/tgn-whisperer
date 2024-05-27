#!/usr/bin/env python3

# Script to unwrap the bit.ly links and save the lookup table
import json
from loguru import logger as log
import time

import requests


if __name__ == '__main__':
    # read the bit.ly links
    raw_links = open('bitly', 'r').readlines()
    links = [link.strip() for link in raw_links]

    rc = json.load(open('bitly.json', 'r'))

    for link in links:
        if link in rc:
            log.debug(f"Skipping {link}, already in lookup table")
            continue
        log.debug(f'Fetching {link}...')
        # get the expanded url
        expanded = requests.get(link).url
        rc[link] = expanded
        log.info(f'{link} -> {expanded}')
        # save the lookup table
        log.info(f'Writing lookup table to bitly.json')
        json.dump(rc, open('bitly.json', 'w'), indent=2)
        log.debug('Sleeping 15 seconds...')
        time.sleep(15)

    log.info(f'Done! {len(rc)} links in lookup table')