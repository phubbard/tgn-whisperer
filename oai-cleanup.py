#!/usr/bin/env python3

# OctoAI returns an annoying format. This script chunks that up. Seems like they should provide this, but whatevs.
from collections import defaultdict
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(pathname)s(%(lineno)s): %(levelname)s %(message)s')
log = logging.getLogger()


if __name__ == '__main__':
    log.info('Reading episode...')
    episode = json.load(open('episode-transcribed.json', 'r'))
    log.info('Processing')
    rc = []
    speaker = None
    text_chunk = ''
    start = None
    for chunk in episode['response']['segments']:
        # Hmm. Track start/end times and someday link to timestamps in the podcast? Overcast allows this.
        if speaker != chunk['speaker']:
            # Dump the buffered output
            if speaker:
                print(f"{start} {speaker} {text_chunk}")
                rc.append((start, speaker, text_chunk))

            speaker = chunk['speaker']
            text_chunk = chunk['text']
            start = chunk['start']
        else:
            text_chunk += chunk['text']

    print(f"{start} {speaker} {text_chunk}")
    rc.append((start, speaker, text_chunk))

    log.info('Attributing...')
    speakers = set()
    # Count how many speakers were found
    for chunk in rc:
        speakers.add(chunk[1])

    log.info(f"{len(speakers)=} found")
    speaker_map = {}
    speaker_map.setdefault('Unknown')
    for idx in range(10):
        if rc[idx][2].lower().find('james') >= 0:
            speaker_map[rc[idx][1]] = 'James Stacey'
        if rc[idx][2].lower().find('jason') >= 0:
            speaker_map[rc[idx][1]] = 'Jason Heaton'

    for chunk in rc:
        chunk[1] = speaker_map[rc[0]]

    print(rc)

