## Introduction

With my discovery of the [whisper.cpp project](https://github.com/ggerganov/whisper.cpp)
I had the idea of transcribing the podcast of some friends of mine, 
[The Grey Nato](https://thegreynato.com/)

This repo is the code and some notes for myself and others. As of 9/24/2023, the code handles two podcasts and is working 
well. In the octoai branch, I'm working on replacing Whisper.cpp with calls to WhisperX, because that has speaker 
diarization but it's waiting for vendor bugfixes. And it's not free.

## Goals

1. Simple as possible - use existing tools whenever possible
2. Incremental - be able to add new episodes easily and without reworking previous ones

### Workflow and requirements

1. Download the RSS file (process.py, using Requests)
2. Parse it for the episode MP3 files (xmltodict)
3. Convert to 16-bit mono wave files (Whisper's input format) (ffmpeg)
4. Call Whisper on each (command line, note hardwired for Mac/ARM)
5. Export text into markdown files (to_markdown.py)
6. Generate a site with mkdocs
7. Publish (rsync)
8. Profit! (as if)

All of these are run and orchestrated by two Makefiles. Robust, portable, deletes
outputs if interrupted, working pretty well. Note that the loop-over-episodes is a shell loop - this is a TODO.

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

however! TGN was bad, and didn't include this. What's more, they had episodes _in between_ episodes. The episode_number
function in process.py handles this with a combination of techniques:

1. Try the itunes:episode key
2. Check the list of exceptions, keyed by string title
3. Try to parse an integer from the title
4. Starting at 2100, assign a number

The story is very similar for per-episode URLs. Should be there, often are missing, and can sometimes be parsed out of the description.

40 & 20 has clean metadata, so this was a _ton_ easier for their feed.

### Optional - wordcloud

I was curious as to how this'd look, so I used the Python wordcloud tool. A bit fussy
to work with my [python 3.11 install](https://github.com/amueller/word_cloud/issues/708):

	 python -m pip install -e git+https://github.com/amueller/word_cloud#egg=wordcloud
	 cat tgn/*.txt > alltext
	 wordcloud_cli --text alltext --imagefile wordcloud.png --width 1600 --height 1200

![wordcloud](archive/wordcloud.png "TGN wordcloud")

40 & 20, run Sep 24 2023 - fun to see the overlaps.

![wordcloud_wcl](archive/wordcloud_wcl.png "40 & 20 wordcloud)

# Further work and open questions

1. email notifications on new episodes
2. WhisperX
3. Performance improvements (in progress - the Makefile rewrites were huge)