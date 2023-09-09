## Introduction

With my discovery of the [whisper.cpp project](https://github.com/ggerganov/whisper.cpp)
I had the idea of transcribing the podcast of some friends of mine, 
[The Grey Nato](https://thegreynato.com/) initially, and now also [40 and 20](https://watchclicker.com/4020-the-watch-clicker-podcast/)

It's running on my trusty M1 Mac Mini. The Whisper.cpp binary is ARM-only.

After I got this working, an acquaintance on the TGN Slack pinged me to try their [OctoAI paid/hosted version](https://octoml.ai/models/whisper/) 
with speaker diarization. Off we go!

This repo is the code and some notes for myself and others.

## Goals

1. Simple as possible - use existing tools whenever possible
2. Incremental - be able to add new episodes easily and without reworking previous ones

### Workflow

1. Download the RSS file
2. For each episode, generate the JSON file for OctoAI (URL of MP3, mainly)
3. Call OctoAI (either via commandline, wget or SDK. TBD.)
4. Generate episode.txt
2. Parse it for the episode MP3 files
5. Export text into markdown files
6. Generate a site with mkdocs
7. Publish
8. Profit! Actually, no, this is a for-fun side hack. Try to keep the costs down.

All of these are run and orchestrated by a multi-rule Makefile. Robust, portable, deletes
outputs if interrupted, working pretty well. 

### Code notes and requirements

1. Python Requests to download the RSS
2. wget to download the HTML and MP3
3. OctoAI for speech to text.
4. Whisper.cpp binary and associated language model
4. 
4. Python + xmltodict for generating output
5. jq for parsing my json into urls and such
5. mkdocs for site generation

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

### Optional - wordcloud

I was curious as to how this'd look, so I used the Python wordcloud tool. A bit fussy
to work with my [python 3.11 install](https://github.com/amueller/word_cloud/issues/708):

	 python -m pip install -e git+https://github.com/amueller/word_cloud#egg=wordcloud
	 cat tgn/*.txt > alltext
	 wordcloud_cli --text alltext --imagefile wordcloud.png --width 1600 --height 1200

![wordcloud](archive/wordcloud.png "TGN wordcloud")

# Further work and open questions

