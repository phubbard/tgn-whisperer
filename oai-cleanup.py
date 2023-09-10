#!/usr/bin/env python3

# OctoAI returns an annoying format. This script chunks that up. Seems like they should provide this, but whatevs.
from collections import defaultdict, Counter
import json
import logging
from pprint import pprint

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

    # Now we have an array of chunks, each of which is a tuple of start time, speaker, text. Can we name the speakers?
    log.info('Attributing...')
    speakers = set()
    # Count how many speakers were found
    for chunk in rc:
        speakers.add(chunk[1])
    log.info(f"{len(speakers)=} found")

    # Build a lookup table / map e.g.
    # SPEAKER_00 : "James Stacey"
    speaker_map = defaultdict(lambda: 'Unknown')

    s_counter = Counter()

    # Look in the first few chunks for speakers identifying themselves
    for idx in range(10):
        if rc[idx][2].lower().find('james') >= 0:
            if s_counter['james'] > 0:
                continue
            speaker_map[rc[idx][1]] = 'James Stacey'

            s_counter.update(['james'])
        if rc[idx][2].lower().find('jason') >= 0:
            if s_counter['jason'] > 0:
                continue
            speaker_map[rc[idx][1]] = 'Jason Heaton'
            s_counter.update(['jason'])

    print(f'{speaker_map=}')

    for idx, _ in enumerate(rc):
        rc[idx] = (rc[idx][0], speaker_map[rc[idx][1]], rc[idx][2])

    # Time to make some markdown
    body = '|*Time(sec)*|*Speaker*||\n|----|----|----|\n'
    for idx, chunk in enumerate(rc):
        # TODO word wrap text
        body += f"|{chunk[0]}|{chunk[1]}|{chunk[2]}|\n"

    fh = open('episode.md', 'w')
    fh.write(body)
    fh.close()
