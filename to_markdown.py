#!/usr/bin/env python3
# Script to extract metadata from the episode.json file and create a markdown file and merge
# the episode.txt file into it. Could be done with jq and shell script, but this is easier much simpler.

# TODO: Merge in per-episode links and text parsed from the HTML.

import json

if __name__ == '__main__':
    episode = json.load(open('episode.json', 'r'))
    md_string = f'''
---
title: {episode['title']}
date: {episode['pub_date']}
number: {episode['number']}
---

# {episode['title']}
Published on {episode['pub_date']}

# Links
- [Episode page]({episode['episode_url']})
- [Episode MP3]({episode['mp3_url']})

# Transcript    
```
{open('episode.txt', 'r').read()}
```
'''
    fh = open('episode.md', 'w')
    fh.write(md_string)
    fh.close()
