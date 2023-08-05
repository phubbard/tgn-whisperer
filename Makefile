# deps: whisper.cpp, ffmpeg, wget
# pfh 2/21/2023 learning from https://makefiletutorial.com
# and https://www.gnu.org/software/make/manual/html_node/File-Name-Functions.html
# Can split the rss into files using
# cat links | cut -f 5 -d / | xargs touch

# FIXME - this wildcard runs at start, before the DL/parse. Need to re-run post download.
mp3files := $(wildcard tgn/*.mp3)
wavfiles := $(mp3files:mp3=wav)
txtfiles := $(mp3files:mp3=txt)
mdfiles := $(mp3files:mp3=md)
htmlfiles := $(mp3files:mp3=html)

.PHONY: all
.DELETE_ON_ERROR:
all: rss links mp3s $(wavfiles) $(txtfiles) $(htmlfiles) $(mdfiles) site

# How to run this in parallel? gnu parallel or let Make determine?
$(wavfiles): %.wav: %.mp3
	ffmpeg -i $< -ar 16000 -ac 1 -c:a pcm_s16le $@
	
# This should be one instance - does its own parallelism
# Need to strip the file extension though
$(txtfiles): %.txt: %.wav
	./main -m models/ggml-base.en.bin -nt -pp -f $< -otxt -of $(basename $<)


htmlfetcher: rss
	python3 episode_links.py > htmlfetcher.sh
	chmod 755 htmlfetcher.sh
	./htmlfetcher.sh

rss:
	# Might be cleaner / more Make-like to split each URL into a separate file. Hmm.
	wget -N https://feeds.buzzsprout.com/2049759.rss

links: rss
    # Uses grep to parse MP3 URL links from the RSS feed.
	grep -Eo "(http|https)://[a-zA-Z0-9./?=_%:-]*mp3" *.rss > links
	wc -l links

mp3s: links
	# This could also run in parallel.
	wget -i links -P tgn -nc

mdf: htmlfetcher
	python3 export.py

site: mdf
	cp tgn/*.md TheGreyNATO/docs
	cd TheGreyNATO
	mkdocs build

.PHONY: clean
clean:
	-rm *.rss links episode_links $(wavfiles) $(txtfiles) $(htmlfiles) $(mdfiles) $(mp3files)

.PHONY: distclean
distclean:
	-rm $(mp3files) $(wavfiles) $(txtfiles) *.rss data.json $(database)