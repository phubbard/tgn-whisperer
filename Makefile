# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:
all: rss directories episodes site

rss:
	wget --no-use-server-timestamps -N https://feed.podbean.com/the40and20podcast/feed.xml

directories: rss
	python3 process.py

episodes: directories
	for dir in $(dir $(wildcard 40and20episodes/*/.)); do \
  		echo $$ddir; \
		cd $$dir; \
		$(MAKE) -f ../Makefile; \
		cd ../../; \
	done

site: episodes
	cd 40and20; \
	mkdocs build

.PHONY: clean
clean:
	-rm *.rss

