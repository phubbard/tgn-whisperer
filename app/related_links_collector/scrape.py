import json
import time
import logging
from typing import Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from bs4 import BeautifulSoup
from .utils import domain as dom_of
from .extractors import extract_substack_any, nearest_related_container, extract_items

class Transient(Exception):
    pass

@retry(reraise=True, stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type(Transient))
def fetch(url: str, session: requests.Session) -> requests.Response:
    try:
        r = session.get(url, timeout=30)
        if r.status_code in (429, 502, 503, 504):
            raise Transient(f"HTTP {r.status_code}")
        r.raise_for_status()
        return r
    except requests.HTTPError as e:
        if 500 <= e.response.status_code < 600:
            raise Transient(str(e))
        raise

def run(urls_path: str, out_path: str, exceptions_path: str,
        overrides_path: Optional[str] = None, rate: float = 1.2,
        log: Optional[logging.Logger] = None) -> None:
    """
    Scrape related links from episode pages.

    IMPORTANT: The out_path file is a PERMANENT CACHE. It should never be deleted.
    This function appends to the file and skips URLs that already have successful scrapes.
    Scraping is expensive (1-2 hours for 361 episodes), so preserving this cache is critical.

    Args:
        urls_path: File with one URL per line to scrape
        out_path: JSONL file to append results (PERMANENT CACHE - never delete!)
        exceptions_path: JSONL file to append errors
        overrides_path: Optional YAML file with custom CSS selectors per domain
        rate: Minimum seconds between requests to the same domain
        log: Logger instance
    """
    log = log or logging.getLogger(__name__)
    overrides = {}
    if overrides_path:
        try:
            import yaml
            with open(overrides_path, "r", encoding="utf-8") as f:
                overrides = yaml.safe_load(f) or {}
        except FileNotFoundError:
            log.warning("Overrides file not found: %s", overrides_path)
        except Exception as e:
            log.warning("Failed to load overrides: %s", e)

    # Load already processed URLs from existing cache file
    # This allows incremental scraping - only new episodes need to be scraped
    processed_urls = set()
    try:
        with open(out_path, "r", encoding="utf-8") as existing:
            for line in existing:
                try:
                    rec = json.loads(line)
                    if rec.get("status") in ("ok", "skipped_robots"):
                        processed_urls.add(rec.get("source_url"))
                except Exception:
                    pass
        if processed_urls:
            log.info("Found %d already-scraped URLs in cache, will skip them", len(processed_urls))
    except FileNotFoundError:
        pass

    per_domain_sleep = {}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })

    with open(out_path, "a", encoding="utf-8") as out, \
        open(exceptions_path, "a", encoding="utf-8") as exc_out, \
        open(urls_path, "r", encoding="utf-8") as f_urls:

        for raw in f_urls:
            url = raw.strip()
            if not url:
                continue

            # Skip if already processed
            if url in processed_urls:
                log.info("Skipping already-processed URL: %s", url)
                continue

            d = dom_of(url)
            try:
                # Robots.txt check disabled
                # if not can_fetch(url):
                #     msg = {"source_url": url, "status": "skipped_robots", "related": []}
                #     out.write(json.dumps(msg) + "\n")
                #     log.info("Skipped by robots.txt: %s", url)
                #     continue

                last = per_domain_sleep.get(d)
                if rate and last is not None:
                    delta = time.time() - last
                    if delta < rate:
                        time.sleep(rate - delta)

                r = fetch(url, session)
                per_domain_sleep[d] = time.time()

                html = r.text
                soup = BeautifulSoup(html, "lxml")

                if d.endswith("substack.com"):
                    items = extract_substack_any(html, str(r.url), client=session)
                    selector_used = "substack_show_notes_any"
                else:
                    ovr = (overrides.get(d, {}) or {}).get("selector")
                    nodes = nearest_related_container(soup, override_selector=ovr)
                    items = extract_items(nodes, str(r.url), client=session)
                    selector_used = ovr or "heuristic"

                rec = {
                    "source_url": str(r.url),
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "ok",
                    "selector_used": selector_used,
                    "related": items
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                log.info("OK %s -> %d items", url, len(items))

            except Exception as e:
                err = {"source_url": url, "status": "error", "error": str(e)}
                exc_out.write(json.dumps(err, ensure_ascii=False) + "\n")
                log.error("ERROR %s -> %s", url, e)

    session.close()
