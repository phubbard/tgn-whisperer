# pfh 8/5/2023, rethinking - now one director per episode, with all files in it. New parent-level make for that.

.PHONY: all
.DELETE_ON_ERROR:
all: rss directories episodes site

rss:
	# Might be cleaner / more Make-like to split each URL into a separate file. Hmm.
	wget -N https://feeds.buzzsprout.com/2049759.rss

directories: rss
	python3 process.py

episodes: directories
	cd episodes
	for dir in $(dir $(wildcard episodes/*/.)); do \
		cd $$dir; \
		$(MAKE) -f ../Makefile; \
		cd ..; \
	done

site: mdf
	cd TheGreyNATO
	mkdocs build

.PHONY: clean
clean:
	-rm *.rss links episode_links $(wavfiles) $(txtfiles) $(htmlfiles) $(mdfiles) $(mp3files)

