#!/usr/bin/env python3

# OctoAI returns an annoying format. This script chunks that up. Seems like they should provide this, but whatevs.
# Now that chunking works, I want a fast, interactive way to do speaker attribution, such that the transcript has
# proper names on it. I had code that did one TGN intro, but i wasn't happy with it so I'm trying a new approach.

from collections import defaultdict
import json

# See https://github.com/petereon/beaupy
from beaupy import confirm, prompt, select, select_multiple, Config
from rich.console import Console
config = Config()
config.raise_on_interrupt = True
console = Console()

# Heuristics - look for 'Interview' in description
# Look for Andrew or James in first few utterances and prompt for 'is this correct' => 80% solution
# Consider moving speaker map to a separate json file / make target as a next step. then can run
# 'make attribution' as an interactive task but main task runs unattended.


def attribute_podcast(speakers: set, lines: list, possible_speakers: set) -> dict:
    # Build a lookup table / map e.g.
    # SPEAKER_00 : "James Stacey"
    speaker_map = defaultdict(lambda: 'Unknown')
    unknown_speakers = possible_speakers
    done = False
    while unknown_speakers and not done:
        rc = lines.copy()
        unkn_lines = [x for x in rc if x[1] not in speaker_map]
        if not unkn_lines:
            done = True
            continue
        line = unkn_lines[0]
        console.print(f"Which speaker said '{line[2]}'?")
        cur_speaker = select(list(unknown_speakers))
        if cur_speaker:
            speaker_map[line[1]] = cur_speaker
            unknown_speakers.difference(cur_speaker)
        else:
            done = True

    console.print(speaker_map)
    if confirm("Is that map correct and complete?", default_is_yes=True):
        return speaker_map
    return attribute_podcast(speakers, lines, possible_speakers)


def process_transcription():
    console.print('Reading episode...')
    episode = json.load(open('episode-transcribed.json', 'r'))
    console.print('Processing')
    # The default format has chunks of text. We want to append them until the speaker changes.
    rc = []
    speaker = None
    text_chunk = ''
    start = None
    for chunk in episode['response']['segments']:
        # Hmm. Track start/end times and someday link to timestamps in the podcast? Overcast allows this.
        if speaker != chunk['speaker']:
            # Dump the buffered output
            if speaker:
                # print(f"{start} {speaker} {text_chunk}")
                rc.append((start, speaker, text_chunk))

            speaker = chunk['speaker']
            text_chunk = chunk['text']
            start = chunk['start']
        else:
            text_chunk += chunk['text']

    # print(f"{start} {speaker} {text_chunk}")
    rc.append((start, speaker, text_chunk))

    # Now we have an array of chunks, each of which is a tuple of start time, speaker, text. Can we name the speakers?
    console.print('Attributing...')

    speakers = set()
    # Count how many speakers were found
    for chunk in rc:
        speakers.add(chunk[1])
    console.print(f"{len(speakers)} unique speakers found")

    for_attrib = []
    for speaker in speakers:
        for line in rc:
            if speaker == line[1]:
                for_attrib.append(line)
                break

    # TODO Filter - send one line from each speaker, not just first few lines.
    speaker_map = attribute_podcast(speakers, for_attrib, set(['James Stacey', 'Jason Heaton', 'Unknown']))
    print(f'{speaker_map=}')

    for idx, _ in enumerate(rc):
        rc[idx] = (rc[idx][0], speaker_map[rc[idx][1]], rc[idx][2])

    # Time to make some markdown
    body = '|*Time(sec)*|*Speaker*||\n|----|----|----|\n'
    for chunk in rc:
        body += f"|{chunk[0]}|{chunk[1]}|{chunk[2]}|\n"

    fh = open('episode.md', 'w')
    fh.write(body)
    fh.close()


if __name__ == '__main__':
    process_transcription()
