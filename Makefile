# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:
all: directories episodes site deploy

directories: 
	python3 app/process.py

episodes: directories
	for dir in $(dir $(wildcard podcasts/*/*/.)); do \
  		echo $$dir; \
		cd $$dir; \
		$(MAKE) -f ../../../episode_makefile; \
		cd ../../../; \
	done

site:
	for dir in $(dir $(wildcard sites/*/.)); do \
  		echo $$dir; \
		cd $$dir; \
		mkdocs build; \
		cd ../../; \
	done	

deploy:
	cd sites/tgn/site; \
	scp -r * usul:html/tgn; \
	cd ../../wcl/site; \
	scp -r * usul:html/wcl; \

.PHONY: clean
clean:
	-rm -rf podcasts/*/episodes/* sites/*/site

