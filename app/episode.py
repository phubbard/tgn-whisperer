#!/usr/bin/env python3
import json
import sys
from collections import defaultdict
from pathlib import Path

# See https://github.com/petereon/beaupy
from beaupy import confirm, prompt, select, select_multiple, Config
from rich.console import Console

EPISODE_TRANSCRIBED_JSON = 'episode-transcribed.json'
SPEAKER_MAP = 'speaker-map.json'

# OctoAI returns an annoying format. This script chunks that up. Seems like they should provide this, but whatevs.
# Now that chunking works, I want a fast, interactive way to do speaker attribution, such that the transcript has
# proper names on it. I had code that did one TGN intro, but i wasn't happy with it so I'm trying a new approach.

UNKNOWN = 'Unknown'
NEW_NAME = '- New name'

config = Config()
config.raise_on_interrupt = True
console = Console()


# Heuristics - look for 'Interview' in description
# Look for Andrew or James in first few utterances and prompt for 'is this correct' => 80% solution
# Consider moving speaker map to a separate json file / make target as a next step. then can run
# 'make attribution' as an interactive task but main task runs unattended.
def tgn_heuristic(first_utterance: str, description: str) -> dict:
    if 'my name is james' in first_utterance.lower() and 'interview' not in description.lower():
        rc = defaultdict(lambda: UNKNOWN)
        rc['SPEAKER_00'] = 'James Stacey'
        rc['SPEAKER_01'] = 'Jason Heaton'
        return rc


def wcl_heuristic(first_utterance: str, description: str) -> dict:
    if 'andrew and my good friend everett' in first_utterance.lower() and 'interview' not in description.lower():
        rc = defaultdict(lambda: UNKNOWN)
        rc['SPEAKER_00'] = 'Andrew'
        rc['SPEAKER_01'] = 'Everett'
        return rc


def attribute_podcast(speakers: set, lines: list, possible_speakers: set) -> dict:
    # TODO: add ability to print surrounding lines to resolve ambiguity. Need to pass indices instead of contents.
    # Build a lookup table / map e.g.
    # SPEAKER_00 : "James Stacey"
    speaker_map = defaultdict(lambda: UNKNOWN)
    unknown_speakers = possible_speakers.copy()
    done = False
    while unknown_speakers and not done:
        console.print('')
        all_lines = lines.copy()
        unkn_lines = [x for x in all_lines if x[1] not in speaker_map]
        if not unkn_lines:
            done = True
            continue
        # Work on one line at a time
        line = unkn_lines[0]
        console.print(f'[red]Which person said [/][green]"{line[2]}"[/]?')
        # TODO look for name in line and sort choices
        choices = list(unknown_speakers)
        choices.append(UNKNOWN)
        choices.append(NEW_NAME)
        selection = select(choices)
        if selection:
            if selection == NEW_NAME:
                selection = prompt('Enter new name', target_type=str, validator=lambda x: len(x) > 1)
            speaker_map[line[1]] = selection
            unknown_speakers.discard(selection)
        else:
            done = True

    console.print('Done attributing.')
    for key in speaker_map.keys():
        console.print(f"{key} is {speaker_map[key]}")
    #
    choices = ['Accept', 'Redo', 'Abort']
    selection = select(choices)
    if selection == 'Accept':
        return speaker_map
    if selection == 'Redo':
        return attribute_podcast(speakers, lines, possible_speakers)
    return {}


def process_transcription():
    console.print('Reading episode...')
    episode = json.load(open(EPISODE_TRANSCRIBED_JSON, 'r'))
    episode_json = json.load(open('episode.json', 'r'))

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
                rc.append((start, speaker, text_chunk))

            speaker = chunk['speaker']
            text_chunk = chunk['text']
            start = chunk['start']
        else:
            text_chunk += chunk['text']

    rc.append((start, speaker, text_chunk))

    # Now we have an array of chunks, each of which is a tuple of start time, speaker, text. Can we name the speakers?
    console.print('Attributing...')

    speakers = set()
    # Count how many speakers were found
    for chunk in rc:
        speakers.add(chunk[1])
    console.print(f"{len(speakers)} unique speakers found")

    # Filter - send one line from each speaker, not just first few lines.
    for_attrib = []
    for speaker in speakers:
        for line in rc:
            if speaker == line[1]:
                for_attrib.append(line)
                break

    # Guess the podcast based on finding tgn or wcl in the path.
    cur_file = Path(EPISODE_TRANSCRIBED_JSON)
    fullpath = str(cur_file.absolute())
    heuristic = None
    if 'wcl' in fullpath:
        console.print('Guessing 40 and 20')
        possible_speakers = {'Andrew', 'Everett'}
        heuristic = wcl_heuristic
    elif 'tgn' in fullpath:
        console.print('Guessing TGN')
        possible_speakers = {'James Stacey', 'Jason Heaton'}
        heuristic = tgn_heuristic
    else:
        raise Exception('Unknown podcast')

    sm_file = Path(SPEAKER_MAP)
    if sm_file.exists():
        console.print(f'Reprocessing from existing {SPEAKER_MAP}')
        file_map = json.load(open(SPEAKER_MAP, 'r'))
        speaker_map = defaultdict(lambda: UNKNOWN)  # FIXME make this a shared/global
        speaker_map.update(file_map)
    else:
        auto = heuristic(rc[0][2], episode_json['title'])
        if auto is None:
            console.print('Manual attribution required, heuristic failed.')
            speaker_map = attribute_podcast(speakers, for_attrib, possible_speakers)
        else:
            console.print(f'Auto-attributed episode {episode_json["title"]}')
            speaker_map = auto

    if not speaker_map:
        console.print('Aborting attribution')
        sys.exit(1)

    json.dump(speaker_map, open(SPEAKER_MAP, 'w'))

    # Now use the map
    for idx, _ in enumerate(rc):
        rc[idx] = (rc[idx][0], speaker_map[rc[idx][1]], rc[idx][2])

    # Time to make some markdown
    md_string = f'''
    # {episode_json['title']}
    Published on {episode_json['pub_date']}

    {episode_json['subtitle']}

    # Links
    - [episode page]({episode_json['episode_url']})
    - [episode MP3]({episode_json['mp3_url']})
    - [episode text](episode.txt)
    - [episode webpage snapshot](episode.html)
    - [episode MP3 - local mirror](episode.mp3)

    # Transcript    
    '''
    fh = open('episode.md', 'w')
    fh.write(md_string)

    body = '|*Time(sec)*|*Speaker*||\n|----|----|----|\n'
    for chunk in rc:
        body += f"|{chunk[0]}|{chunk[1]}|{chunk[2]}|\n"

    fh.write(body)
    fh.close()


if __name__ == '__main__':
    process_transcription()
