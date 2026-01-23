## Introduction

With my discovery of the [whisper.cpp project](https://github.com/ggerganov/whisper.cpp)
I had the idea of transcribing the podcast of some friends of mine, 
[The Grey Nato](https://thegreynato.com/) initially, and now also the [40 and 20](https://watchclicker.com/4020-the-watch-clicker-podcast/) 
podcast that I also enjoy.

As of mid-2025, the code runs on 
- Raspberry Pi v4 runs the main orchestration code
- Ollama on my Mac studio runs WhisperX for speech to text plus diarization - [code here](https://github.com/phubbard/flask-whisperx)
- Paid API call to Anthropic to do speaker attribution
- Caddy2 on the same RPi to serve the files

The results (static websites) are deployed to

- [The Compleat Grey Nato](https://tgn.phfactor.net/)
- [The Compleat 40 & 20](https://wcl.phfactor.net/)
- [The Compleat Hodinkee Radio](https://hodinkee.phfactor.net/)

Take a look! This code and the sites are provided free of charge as a public service to fellow fans, listeners and those who
find the results useful.

This repo is the code and some notes for myself and others. As of January 2026, the code handles three podcasts (TGN, WCL, and Hodinkee Radio) and is working well. 

## Goals

1. Simple as possible - use existing tools whenever possible
2. Incremental - be able to add new episodes easily and without reworking previous ones

### Workflow and requirements

1. Download the RSS file (process.py, using Requests)
2. Parse it for the episode MP3 files (xmltodict)
4. Call WhisperX on each (POST to Flask)
5. Collation and speaker attribution (episode.py)
5. Export text into markdown files (to_markdown.py)
6. Generate a site with mkdocs
7. Generate search index with [Pagefind](https://pagefind.app/docs/)
8. Publish (rsync)

All of these are run and orchestrated by two Makefiles. Robust, portable, deletes
outputs if interrupted, working pretty well. 

Makefiles are tricky to write and debug. I might need [remake](https://remake.readthedocs.io/en/latest/) at some point. The [makefile tutorial here](https://makefiletutorial.com/) was essential at several points - suffix rewriting, basename built-in, phony, etc. You can do a _lot_ with a Makefile very concisely, and the result is robust, portable and durable. And fast.

Another good tutorial (via Lobste.rs) [https://makefiletutorial.com/#top](https://makefiletutorial.com)

Directory [list from StackOverflow](https://stackoverflow.com/questions/13897945/wildcard-to-obtain-list-of-all-directories) ... as one does.

### The curse of URL shorteners and bit.ly in particular

For a while, the TGN podcast shared episode URLs with bit.ly. There are good reasons for this, but now when I want to 
sequentially retrieve pages, the bit.ly throws rate limits and I see no reason to risk errors for readers. So I've 
built a manual process:

- Grep the RSS file for bit.ly URLs
- Save same into a text file called bitly
- Run the unwrap-bitly.py script to build a json dictionary that resolves them
- The process.py will use the lookup dictionary and save the canonical URLs.

### Episode numbers and URLs

For a project like this, you want a primary index / key / way to refer to an episode. The natural choice is "episode number". This is a field in the RSS XML:

    itunes:episode

However, many podcast RSS feeds have missing or incomplete episode numbers. To solve this, we use a generalized RSS processor (`rss_processor.py`) that:

1. Downloads the RSS feed
2. Fills in missing `itunes:episode` tags chronologically (oldest = 1, newest = N)
3. Preserves existing episode numbers where they exist
4. Avoids creating duplicate numbers

After processing, all episodes have `itunes:episode` tags, and `process.py` simply reads them directly - no more complex title parsing or hardcoded lookup dictionaries!

The story is similar for per-episode URLs. Should be there, often are missing, and can sometimes be parsed out of the description.

**Testing**: Run `pytest test_rss_processing.py` to verify the RSS processor works correctly with all podcast feeds.

### Optional - wordcloud

I was curious as to how this'd look, so I used the Python wordcloud tool. A bit fussy
to work with my [python 3.11 install](https://github.com/amueller/word_cloud/issues/708):

	 python -m pip install -e git+https://github.com/amueller/word_cloud#egg=wordcloud
	 cat tgn/*.txt > alltext
	 wordcloud_cli --text alltext --imagefile wordcloud.png --width 1600 --height 1200

![wordcloud](archive/wordcloud.png "TGN wordcloud")

40 & 20, run Sep 24 2023 - fun to see the overlaps.

![wordcloud_wcl](archive/wordcloud_wcl.png "40 & 20 wordcloud")
