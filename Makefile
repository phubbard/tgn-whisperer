# pfh 8/5/2023, rethinking - now one directory per episode, with all files in it.
# New parent-level make for that that iterates over all episode directories and calls
# the episode-level makefile.

.PHONY: all
.DELETE_ON_ERROR:
all: directories episodes site deploy

directories: 
	python3 app/process.py



PODCAST_ROOT := podcasts

PODCAST_DIRS := $(dir $(wildcard $(PODCAST_ROOT)/*/*/.))


.PHONY: \
bradstart
bradstart: 
	@echo BRADRULE: starting


$(PODCAST_ROOT)/%: bradstart
	@$(MAKE) -C $(PODCAST_ROOT)/$* -f $(CURDIR)/episode_makefile talk


brad:
	@echo BRADRULE: PODCAST_DIRS = $(PODCAST_DIRS)
	false


bradloop: $(PODCAST_DIRS)
	@echo BRADRULE: finished




episodes: directories
	@for dir in $(dir $(wildcard podcasts/*/*/.)); do \
		cd $$dir; \
		$(MAKE) -f ../../../episode_makefile; \
		cd ../../../; \
	done

site:
	@for dir in $(dir $(wildcard sites/*/.)); do \
		cd $$dir; \
		mkdocs build; \
		cd ../../; \
	done	

deploy:
	cd sites/tgn/site; \
	@echo Deploying TGN...; \
	rsync -au --progress . usul:html/tgn; \
	cd ../../wcl/site; \
	@echo Deploying 40 and 20...; \
	rsync -au --progress . usul:html/wcl; \

.PHONY: clean
clean:
	-rm -rf podcasts/*/episodes/* sites/*/site

