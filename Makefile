# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:

SITE_LIST    := tgn wcl

PODCAST_ROOT := podcasts
PODCAST_EPS  := $(patsubst %,%/episode.md,$(dir $(wildcard $(PODCAST_ROOT)/*/*/.)))
SITE_ROOT    := sites
SITE_INDEXES := $(patsubst %,$(SITE_ROOT)/%/site/index.html, $(SITE_LIST))

all:
	@$(MAKE) directories
	@$(MAKE) episodes
	@$(MAKE) deploy

# This step creates the per-episode directories, if they don't already exist.
directories:
	@python3 app/process.py

$(PODCAST_ROOT)/%/episode.md: directories
	@$(MAKE) -s -C $(PODCAST_ROOT)/$* -f $(CURDIR)/episode_makefile

episodes: $(PODCAST_EPS)

$(SITE_ROOT)/%/site/index.html: $(SITE_ROOT)/%/docs/episodes.md
	cd $(SITE_ROOT)/$*  &&  mkdocs -q build
	cd $(SITE_ROOT)/$*/site  && rsync -qrpgD --delete --force . /usr/local/www/$*

deploy: $(SITE_INDEXES)

