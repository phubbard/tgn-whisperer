# pfh 8/5/2023, rethinking - now one director per episode, with all files in it. New parent-level make for that.

# This one's jobs are:
# - Download the RSS feed into a file
# - Use regex to extract all MP3 links from the RSS feed
# - For each file:
# -- mkdir `basename`
# -- mv mp3 into `basename`


# FIXME - this wildcard runs at start, before the DL/parse. Need to re-run post download.
mp3files := $(wildcard tgn/*.mp3)
directories += $(basename $(mp3files))

.PHONY: all
.DELETE_ON_ERROR:
all: rss links

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