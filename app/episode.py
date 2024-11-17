#!/usr/bin/env python3
import json
import os
from collections import defaultdict
from pathlib import Path

import anthropic
from loguru import logger as log
from attribute import process_episode

from constants import *

# OctoAI returns an annoying format. This script chunks that up. Seems like they should provide this, but whatevs.
# Now that chunking works, I want a fast, interactive way to do speaker attribution, such that the transcript has
# proper names on it. I had code that did one TGN intro, but i wasn't happy with it so I'm trying a new approach.


def process_transcription():
    log.info('Reading episode...')
    episode = json.load(open(EPISODE_TRANSCRIBED_JSON, 'r'))
    episode_json = json.load(open('episode.json', 'r'))

    # The default format has chunks of text. We want to append them until the speaker changes.
    rc = []
    speaker = None
    text_chunk = ''
    start = None
    for chunk in episode['segments']:
        if not 'speaker' in chunk:
            log.warning(f'No speaker in chunk: {chunk}')
            continue
        # Add space after punctuation
        punctuation = ['.', '?', '!']
        char = chunk['text'][-1]
        if char in punctuation:
            chunk['text'] += ' '

        # TODO Hmm. Track start/end times and someday link to timestamps in the podcast? Overcast allows this.
        if speaker != chunk['speaker']:
            # Dump the buffered output
            if speaker:
                rc.append((start, speaker, text_chunk))

            speaker = chunk['speaker']
            text_chunk = chunk['text']
            start = chunk['start']
        else:
            text_chunk += chunk['text']

    rc.append((start, speaker, text_chunk))

    # Save the Whisper output to send to Claude for speaker attribution
    with open('whisper-output.json', 'w') as fh:
        json.dump(rc, fh)

    # Now we have an array of chunks, each of which is a tuple of start time, speaker, text. Can we name the speakers?
    log.info('Attributing...')

    # Get cwd    
    cwd = Path('.').absolute()

    try:
        speaker_map, synopsis = process_episode(directory=cwd)
    except anthropic.RateLimitError as e:
        log.error("Rate limit exceeded. Try again later.")
        raise e
    except IndexError:
        log.error("Exception calling attribution/synopsis")
        speaker_map = defaultdict(lambda: "Unknown")
        synopsis = "LLM-exception"

    # Now use the map
    for idx, _ in enumerate(rc):
        rc[idx] = (rc[idx][0], speaker_map[rc[idx][1]], rc[idx][2])

    # Time to make some markdown
    md_string = f'''
# {episode_json['title']}
Published on {episode_json['pub_date']}

{episode_json['subtitle']}

## Synopsis
{synopsis}

## Links
- [episode page]({episode_json['episode_url']})
- [episode MP3]({episode_json['mp3_url']})
- [episode webpage snapshot](episode.html)
- [episode MP3 - local mirror](episode.mp3)

## Transcript    
'''
    fh = open('episode.md', 'w')
    fh.write(md_string)

    body = '|*Speaker*||\n|----|----|\n'
    for chunk in rc:
        body += f"|{chunk[1]}|{chunk[2]}|\n"

    fh.write(body)
    fh.close()


if __name__ == '__main__':
   # os.chdir('/Users/pfh/code/tgn-whisperer/podcasts/tgn/307.0')
   process_transcription()
