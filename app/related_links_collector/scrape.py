import json
import time
import logging
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from bs4 import BeautifulSoup
from .utils import domain as dom_of
from .extractors import extract_substack_any, nearest_related_container, extract_items

class Transient(Exception):
    pass

@retry(reraise=True, stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type(Transient))
def fetch(url: str, client: httpx.Client) -> httpx.Response:
    try:
        r = client.get(url, timeout=30)
        if r.status_code in (429, 502, 503, 504):
            raise Transient(f"HTTP {r.status_code}")
        r.raise_for_status()
        return r
    except httpx.HTTPStatusError as e:
        if 500 <= e.response.status_code < 600:
            raise Transient(str(e))
        raise

def run(urls_path: str, out_path: str, exceptions_path: str,
        overrides_path: Optional[str] = None, rate: float = 1.2,
        log: Optional[logging.Logger] = None) -> None:
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

    # Load already processed URLs from existing output file
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
            log.info("Found %d already-processed URLs, will skip them", len(processed_urls))
    except FileNotFoundError:
        pass

    per_domain_sleep = {}

    with httpx.Client(http2=True, headers={
        "User-Agent": "tgn-whisperer tgn.phfactor.net",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml"
    }, follow_redirects=True) as client, \
        open(out_path, "a", encoding="utf-8") as out, \
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

                r = fetch(url, client)
                per_domain_sleep[d] = time.time()

                html = r.text
                soup = BeautifulSoup(html, "lxml")

                if d.endswith("substack.com"):
                    items = extract_substack_any(html, str(r.url), client=client)
                    selector_used = "substack_show_notes_any"
                else:
                    ovr = (overrides.get(d, {}) or {}).get("selector")
                    nodes = nearest_related_container(soup, override_selector=ovr)
                    items = extract_items(nodes, str(r.url), client=client)
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
