# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:
all: directories episodes sites deploy

SITE_LIST    := tgn wcl

PODCAST_ROOT := podcasts
PODCAST_DIRS := $(dir $(wildcard $(PODCAST_ROOT)/*/*/.))
SITE_ROOT    := siteroots
SITE_INDEXES := $(patsubst %,$(SITE_ROOT)/%/site/index.html, $(SITE_LIST))

directories: 
	python3 app/process.py

$(PODCAST_ROOT)/%: directories
	@$(MAKE) -C $(PODCAST_ROOT)/$* -f $(CURDIR)/episode_makefile

episodes: $(PODCAST_DIRS)
	@echo Finished with all episodes

$(SITE_ROOT)/%/site/index.html: $(SITE_ROOT)/%/docs/episodes.md
	cd $(SITE_ROOT)/$*  &&  mkdocs build

sites: $(SITE_INDEXES)
	@echo sites completed on $(SITE_INDEXES)

# Really excellent rsync reference: https://michael.stapelberg.ch/posts/2022-06-18-rsync-overview/
deploy:
	@echo Deploying TGN...
	cd $(SITE_ROOT)/tgn/site  &&  rsync -a --delete --force --progress . usul:html/tgn
	@echo Deploying 40 and 20...
	cd $(SITE_ROOT)/wcl/site  &&  rsync -a --delete --force --progress . usul:html/wcl

.PHONY: clean
clean:
	-rm -rf $(PODCAST_ROOT)/*/episodes/* $(SITE_ROOT)/*/site

