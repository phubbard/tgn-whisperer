## Introduction

With my discovery of the [whisper.cpp project](https://github.com/ggerganov/whisper.cpp)
I had the idea of transcribing the podcast of some friends of mine, 
[The Grey Nato](https://thegreynato.com/) initially, and now also the [40 and 20](https://watchclicker.com/4020-the-watch-clicker-podcast/) 
podcast that I also enjoy.

As of mid-2025, the code runs on
- Raspberry Pi v4 runs the main orchestration code
- Fluid Audio backend for speech to text plus diarization - [code here](https://github.com/phubbard/fa-web)
- Paid API call to Anthropic to do speaker attribution
- Caddy2 on the same RPi to serve the files

The results (static websites) are deployed to

- [The Compleat Grey Nato](https://tgn.phfactor.net/)
- [The Compleat 40 & 20](https://wcl.phfactor.net/)
- [The Compleat Hodinkee Radio](https://hodinkee.phfactor.net/)

Take a look! This code and the sites are provided free of charge as a public service to fellow fans, listeners and those who
find the results useful.

This repo is the code and some notes for myself and others. As of January 2026, the code handles three podcasts (TGN, WCL, and Hodinkee Radio) and is working well. 

## Goals

1. Simple as possible - use existing tools whenever possible
2. Incremental - be able to add new episodes easily and without reworking previous ones

## Setup and Dependencies

This project uses [uv](https://docs.astral.sh/uv/) for fast Python dependency management. To get started:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the processing pipeline
uv run make

# Or run Python scripts directly
uv run python app/process.py

# Run tests
uv run pytest app/test_rss_processing.py
```

**Migration note**: This replaces the old `source venv/bin/activate && make` workflow. The old `requirements.txt` is now superseded by `pyproject.toml`.

### Reprocessing Episodes

The `reprocess` utility allows selective rebuilding of episodes with granular control:

```bash
# Full reprocess (remove all generated files and rebuild)
./reprocess tgn 14 --all --make

# Just re-run speaker attribution (useful when Claude attribution fails)
./reprocess wcl 100 --attribute --make

# Re-download and transcribe (useful when audio file changes)
./reprocess hodinkee 246 --download --transcribe --make

# Preview what would be removed without actually removing
./reprocess tgn 361 --all --dry-run
```

**Available flags:**
- `--download` - Remove MP3 file (forces re-download)
- `--transcribe` - Remove transcript files (forces re-transcription)
- `--attribute` - Remove speaker map (forces re-attribution with Claude)
- `--markdown` - Remove markdown files (forces regeneration)
- `--all` - Remove all generated files (full reprocess)
- `--make` - Run make to rebuild after removing files
- `--dry-run` - Preview without actually removing anything

**Episode numbers** can be specified with or without `.0` suffix (e.g., both `14` and `14.0` work).

### Workflow and requirements

1. Download the RSS file (process.py, using Requests)
2. Parse it for the episode MP3 files (xmltodict)
3. Call Fluid Audio backend for transcription and diarization (POST to Flask)
4. Collation and speaker attribution (episode.py, using Claude Sonnet 4.5 API)
5. Export text into markdown files (to_markdown.py)
6. Generate shownotes:
   - **TGN**: Scrape related links from Substack episode pages (related_links_collector)
   - **WCL**: Extract links from RSS feed HTML (wcl_shownotes.py)
7. Generate static sites with mkdocs/zensical
8. Generate search index with [Pagefind](https://pagefind.app/docs/)
9. Publish (rsync)

All of these are run and orchestrated by two Makefiles. Robust, portable, deletes
outputs if interrupted, working pretty well. 

Makefiles are tricky to write and debug. I might need [remake](https://remake.readthedocs.io/en/latest/) at some point. The [makefile tutorial here](https://makefiletutorial.com/) was essential at several points - suffix rewriting, basename built-in, phony, etc. You can do a _lot_ with a Makefile very concisely, and the result is robust, portable and durable. And fast.

Another good tutorial (via Lobste.rs) [https://makefiletutorial.com/#top](https://makefiletutorial.com)

Directory [list from StackOverflow](https://stackoverflow.com/questions/13897945/wildcard-to-obtain-list-of-all-directories) ... as one does.

### The curse of URL shorteners and bit.ly in particular

For a while, the TGN podcast shared episode URLs with bit.ly. There are good reasons for this, but now when I want to 
sequentially retrieve pages, the bit.ly throws rate limits and I see no reason to risk errors for readers. So I've 
built a manual process:

- Grep the RSS file for bit.ly URLs
- Save same into a text file called bitly
- Run the unwrap-bitly.py script to build a json dictionary that resolves them
- The process.py will use the lookup dictionary and save the canonical URLs.

### Episode numbers and URLs

For a project like this, you want a primary index / key / way to refer to an episode. The natural choice is "episode number". This is a field in the RSS XML:

    itunes:episode

However, many podcast RSS feeds have missing or incomplete episode numbers. To solve this, we use a generalized RSS processor (`rss_processor.py`) that:

1. Downloads the RSS feed
2. Fills in missing `itunes:episode` tags chronologically (oldest = 1, newest = N)
3. Preserves existing episode numbers where they exist
4. Avoids creating duplicate numbers

After processing, all episodes have `itunes:episode` tags, and `process.py` simply reads them directly - no more complex title parsing or hardcoded lookup dictionaries!

The story is similar for per-episode URLs. Should be there, often are missing, and can sometimes be parsed out of the description.

**Testing**: Run `pytest test_rss_processing.py` to verify the RSS processor works correctly with all podcast feeds.

### Shownotes Generation

Each podcast has a comprehensive shownotes page listing all related links from every episode:

**The Grey NATO** - Links are extracted by scraping Substack episode pages:
- Uses `related_links_collector` package (integrated from separate repo)
- Workflow: Extract episode URLs → Scrape Substack pages → Resolve shortlinks → Generate markdown
- Handles bit.ly shortlinks via `bitly.json` mapping
- Handles both old and new Substack HTML formats
- Run manually: `uv run python app/generate_tgn_shownotes.py`
- Auto-runs via Makefile when new episodes detected

**40 and 20** - Links are directly in RSS feed:
- Parses HTML from `<description>` and `<content:encoded>` tags
- Filters out boilerplate (sponsors, social media, etc.)
- Run manually: `uv run python app/wcl_shownotes.py`

**Stats**: TGN has 6,611 links from 355 episodes (avg 18.6/episode), WCL has 2,197 links from 275 episodes (avg 8.0/episode).

### Optional - wordcloud

I was curious as to how this'd look, so I used the Python wordcloud tool. A bit fussy
to work with my [python 3.11 install](https://github.com/amueller/word_cloud/issues/708):

	 python -m pip install -e git+https://github.com/amueller/word_cloud#egg=wordcloud
	 cat tgn/*.txt > alltext
	 wordcloud_cli --text alltext --imagefile wordcloud.png --width 1600 --height 1200

![wordcloud](archive/wordcloud.png "TGN wordcloud")

40 & 20, run Sep 24 2023 - fun to see the overlaps.

![wordcloud_wcl](archive/wordcloud_wcl.png "40 & 20 wordcloud")

## Troubleshooting

### Git push hangs

If `git push` hangs, GitHub's SSH port 22 may be blocked by your firewall. Configure SSH to use port 443 instead:

```bash
cat >> ~/.ssh/config << 'EOF'

Host github.com
  Hostname ssh.github.com
  Port 443
  User git
EOF
```

Test with: `ssh -T git@github.com`

### Makefile dependency issues

The project uses careful Makefile dependency management to ensure:
1. RSS feeds are processed before episodes
2. MP3 files are downloaded before transcription
3. Local source files are built before copying to destination
4. Incomplete episodes resume correctly on re-run

If episodes aren't processing, check that source files exist in `podcasts/{podcast}/{episode}/`
