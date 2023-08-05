## Introduction

With my discovery of the [whisper.cpp project](https://github.com/ggerganov/whisper.cpp)
I had the idea of transcribing the podcast of some friends of mine, 
[The Grey Nato](https://thegreynato.com/)

This repo is the code and some notes for myself and others.

## Goals

1. Simple as possible - use existing tools whenever possible
2. Incremental - be able to add new episodes easily and without reworking previous ones

### Workflow

1. Download the RSS file
2. Parse it for the episode MP3 files
3. Convert to 16-bit mono wave files (Whisper's input format)
4. Call Whisper on each
5. Export text into markdown files
6. Generate a site with mkdocs
7. Publish
8. Profit!

All of these are run and orchestrated by a multi-rule Makefile. Robust, portable, deletes
outputs if interrupted, working pretty well. 

### Code notes and requirements

1. wget to download the RSS
2. ffmpeg to transcode to MP3
3. Whisper.cpp binary and associated language model
4. Python + xmltodict for generating output
5. mkdocs for site generation

Makefiles are tricky to write and debug. I might need [remake](https://remake.readthedocs.io/en/latest/) at some point. The [makefile tutorial here](https://makefiletutorial.com/) was essential at several points - suffix rewriting, basename built-in, phony, etc. You can do a _lot_ with a Makefile very concisely, and the result is robust, portable and durable. And fast.

Another good tutorial (via Lobste.rs) [https://makefiletutorial.com/#top](https://makefiletutorial.com)

### Optional - wordcloud

I was curious as to how this'd look, so I used the Python wordcloud tool. A bit fussy
to work with my [python 3.11 install](https://github.com/amueller/word_cloud/issues/708):

	 python -m pip install -e git+https://github.com/amueller/word_cloud#egg=wordcloud
	 cat tgn/*.txt > alltext
	 wordcloud_cli --text alltext --imagefile wordcloud.png --width 1600 --height 1200


# Further work and open questions

1. Finish python and scripting to get the output into a nice site for sharing.
2. Decide output format for whisper - are timestamps useful? Subtitled video for youtube perhaps?
3. Maybe a wordcloud per episode?
4. Add wordcloud as a make target?
5. Compute basic text metrics to share? Words, bytes, ?
