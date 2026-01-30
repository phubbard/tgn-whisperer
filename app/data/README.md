# TGN Shownotes Scraping Cache

## IMPORTANT: Permanent Cache Files

This directory contains **permanent cache files** that should **NEVER be deleted**:

- `tgn_related.jsonl` - Scraped episode data from Substack pages (PERMANENT CACHE)

## Why This Matters

Scraping is:
- **Expensive**: 1-2 hours to scrape 361 episodes
- **Slow**: Rate-limited to 1.2 seconds per page
- **Fragile**: Substack blocks certain HTTP clients (httpx), requires careful UA handling

## How The Cache Works

1. The scraper reads `tgn_related.jsonl` at startup
2. It skips any URLs already present with status "ok"
3. It appends new scraping results to the file
4. Old episode pages never change, so they never need re-scraping

## Cache File Format

Each line is a JSON object:
```json
{
  "source_url": "https://thegreynato.substack.com/p/362-10-years-of-tgn",
  "fetched_at": "2026-01-30T20:49:27Z",
  "status": "ok",
  "selector_used": "substack_show_notes_any",
  "related": [
    {"href": "...", "text": "...", "context": "...", ...}
  ]
}
```

## Updating Shownotes

To add new episodes:

1. **Fetch latest RSS**: `curl -o tgn_feed.rss https://feeds.buzzsprout.com/2049759.rss`
2. **Run shownotes generation**: The scraper automatically skips cached episodes
3. **Only new episodes are scraped**: Typically 1-5 new episodes = 1-10 seconds

## Temporary Working Files

These files are regenerated each run:
- `tgn_urls.txt` - Episode URLs extracted from RSS feed
- `tgn_exceptions.jsonl` - Scraping errors (for debugging)

## Recovery

If the cache is accidentally deleted:
1. Check git history: `git log --all -- app/data/tgn_related.jsonl`
2. Restore from most recent commit
3. If not in git, re-scraping takes ~1-2 hours

## Maintenance

- **Commit cache to git periodically** (after major scraping runs)
- Cache size: ~2.4MB for 319 episodes (~7.5KB per episode)
- Expected max size: ~3MB for all ~400 episodes
