# deps: whisper.cpp, ffmpeg, wget
# pfh 2/21/2023 learning from https://makefiletutorial.com
# and https://www.gnu.org/software/make/manual/html_node/File-Name-Functions.html
# Can split the rss into files using
# cat links | cut -f 5 -d / | xargs touch

# FIXME - this wildcard runs at start, before the DL/parse. 
mp3files := $(wildcard tgn/*.mp3)
wavfiles := $(mp3files:mp3=wav)
txtfiles := $(mp3files:mp3=txt)
htmlfiles := $(mp3files:mp3=html)
jsonfiles := $(mp3files:mp3=json)
database:= tgn.db

.PHONY: all
.DELETE_ON_ERROR:
all: rss links mp3s $(wavfiles) $(txtfiles) $(htmlfiles) $(jsonfiles) database

# How to run this in parallel? gnu parallel or let Make determine?
$(wavfiles): %.wav: %.mp3
	ffmpeg -i $< -ar 16000 -ac 1 -c:a pcm_s16le $@
	
# This should be one instance - does its own parallelism
# Need to strip the file extension though
$(txtfiles): %.txt: %.wav
	./main -m models/ggml-base.en.bin -nt -pp -f $< -otxt -of $(basename $<)


$(htmlfiles): %.html: %.mp3
	wget -O $(basename $<).html $<

rss:
	# Might be cleaner / more Make-like to split each URL into a separate file. Hmm.
	wget -N https://feeds.buzzsprout.com/2049759.rss

links: rss
	grep -Eo "(http|https)://[a-zA-Z0-9./?=_%:-]*mp3" *.rss > links
	wc -l links
	
episode_links: rss
	python3 episode_links.py | sort | uniq > episode_links
	wc -l episode_links

episode_html: episode_links
	wget -i episode_links -P tgn -nc --wait=5 --random-wait --convert-links

mp3s: links
	# This could also run in parallel.
	wget -i links -P tgn -nc

#database: data.json
#	sqlite-utils insert $(database) episodes data.json --pk=id

.PHONY: clean
clean:
	-rm *.rss links episode_links $(database)

.PHONY: distclean
distclean:
	-rm $(mp3files) $(wavfiles) $(txtfiles) *.rss data.json $(database)