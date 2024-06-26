# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:
all: episodes deploy

SITE_LIST    := tgn wcl

PODCAST_ROOT := podcasts
PODCAST_EPS  := $(patsubst %,%/episode.md,$(dir $(wildcard $(PODCAST_ROOT)/*/*/.)))
SITE_ROOT    := sites
SITE_INDEXES := $(patsubst %,$(SITE_ROOT)/%/site/index.html, $(SITE_LIST))

$(PODCAST_ROOT)/%/episode.md:
	@$(MAKE) -C $(PODCAST_ROOT)/$* -f $(CURDIR)/episode_makefile

# directories:
# 	@python3 app/process.py

episodes: $(PODCAST_EPS)

$(SITE_ROOT)/%/site/index.html: $(SITE_ROOT)/%/docs/episodes.md
	cd $(SITE_ROOT)/$*  &&  mkdocs -q build
#	cd $(SITE_ROOT)/$*/site  && rsync -qrpgD --delete --force . usul:html/$*
	cd $(SITE_ROOT)/$*/site  && rsync -qrpgD --delete --force . web:html/$*

deploy: $(SITE_INDEXES)

.PHONY: clean
clean:
	-rm -rf $(PODCAST_ROOT)/*/episodes/* $(SITE_ROOT)/*/site

