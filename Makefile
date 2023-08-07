# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:
all: rss directories episodes site

rss:
	wget --no-use-server-timestamps -N https://feeds.buzzsprout.com/2049759.rss

directories: rss
	python3 process.py

episodes: directories
	cd episodes
	for dir in $(dir $(wildcard episodes/*/.)); do \
		cd $$dir; \
		$(MAKE) -f ../Makefile; \
		cd ../../; \
	done

site: episodes
	cd TheGreyNATO
	mkdocs build

.PHONY: clean
clean:
	-rm *.rss

