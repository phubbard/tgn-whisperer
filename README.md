## Introduction

With my discovery of the [whisper.cpp project](https://github.com/ggerganov/whisper.cpp)
I had the idea of transcribing the podcast of some friends of mine, 
[The Grey Nato](https://thegreynato.com/) initially, and now also the [40 and 20](https://watchclicker.com/4020-the-watch-clicker-podcast/) podcast that I also enjoy.

It's running on my trusty Raspberry Pi v4 and the results (static websites) are deployed to

- [The Compleat Grey Nato](https://tgn.phfactor.net/)
- [The Compleat 40 & 20](https://wcl.phfactor.net/)

Take a look! This code and the sites are provided free of charge as a public service to fellow fans, listeners and those who
find the results useful.

For a year or so we used OctoAI's paid service, but as of 11/1/2024, they're acquired and shut down. So now I'm spinning up [a Flask
wrapper](https://github.com/phubbard/flask-whisperx) for WhisperX on [my compute server](https://ultracrepidarian.phfactor.net/2018/11/17/2018-machine-learning-home-build/). 

This repo is the code and some notes for myself and others. As of 10/9/2023, the code handles two podcasts and is working 
well. 

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
7. Publish (rsync)

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

![wordcloud_wcl](archive/wordcloud_wcl.png "40 & 20 wordcloud")
