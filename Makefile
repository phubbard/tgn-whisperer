# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:
all: rss directories episodes site deploy

rss:
	wget --no-use-server-timestamps -N https://feeds.buzzsprout.com/2049759.rss

directories: rss
	python3 process.py

episodes:
	cd episodes
	for dir in $(dir $(wildcard episodes/*/.)); do \
  		echo $$ddir; \
		cd $$dir; \
		$(MAKE) -f ../Makefile; \
		cd ../../; \
	done

site: 
	cd TheGreyNATO; \
	mkdocs build
	
deploy: 
	cd TheGreyNATO/site; \
	scp -r * usul:html/tgn

.PHONY: clean
clean:
	-rm *.rss

