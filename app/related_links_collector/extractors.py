import re
from typing import List, Optional
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urljoin, urlparse
from .resolvers import resolve_redirectors
from .utils import markdown_link

HEADING_RE = re.compile(r'^(related|see also|further reading|more|you might also like)\b', re.I)

def _segment_children_by_br(parent: Tag):
    seg = []
    for child in parent.children:
        if isinstance(child, Tag) and child.name == "br":
            if seg:
                yield seg
                seg = []
        else:
            seg.append(child)
    if seg:
        yield seg

def _text_content(nodes) -> str:
    out = []
    for n in nodes:
        if isinstance(n, NavigableString):
            out.append(str(n))
        elif isinstance(n, Tag):
            out.extend(list(n.stripped_strings))
    return " ".join(s.strip() for s in out if s and s.strip())

def _is_page_scheme(href: str) -> bool:
    try:
        return (href.startswith("http://") or href.startswith("https://") or href.startswith("/"))
    except Exception:
        return False

def _clean_url(href: str) -> tuple[str, Optional[str]]:
    """
    Clean URLs that may have timestamps or other text concatenated to them.
    Returns (cleaned_url, extracted_timestamp)

    Example: "https://bit.ly/2GDnRSA16:05" -> ("https://bit.ly/2GDnRSA", "16:05")
    """
    try:
        # Check for timestamp pattern at the end of URL
        # Matches patterns like: 16:05, 1:23:45, etc.
        match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*$', href)
        if match:
            timestamp = match.group(1)
            clean_href = href[:match.start()]
            return (clean_href, timestamp)
        return (href, None)
    except Exception:
        return (href, None)

def _extract_substack_fallback(container: Tag, base_url: str, client=None) -> List[dict]:
    """
    Fallback extractor for older Substack format where links are scattered
    across multiple paragraphs without <br> tags.
    """
    items, pos = [], 0

    # Collect all paragraphs with links
    for p in container.find_all("p", recursive=True):
        links = p.find_all("a", href=True)
        if not links:
            continue

        for a in links:
            href_raw = urljoin(base_url, a.get("data-href") or a.get("href"))
            if not _is_page_scheme(href_raw):
                continue

            # Clean URLs that may have timestamps concatenated
            href_raw_clean, extracted_timestamp = _clean_url(href_raw)
            href_clean = resolve_redirectors(href_raw_clean, client=client)

            a_text = " ".join(a.stripped_strings) if a else ""
            p_text = " ".join(p.stripped_strings)

            # In old format, descriptive text comes before the link
            # Format: "Description: url" where url is the link text
            # Extract the description part as the display text
            context = None
            display_text = a_text

            if a_text and a_text in p_text:
                # Split on the link text to get what comes before
                before_link = p_text.split(a_text)[0].strip(" –—:;")
                if before_link and before_link != a_text:
                    # Use the descriptive text before the link as display text
                    display_text = before_link
                    context = None  # Don't need context when we have good display text

            if not display_text or display_text == a_text:
                display_text = a_text or href_clean

            items.append({
                "href": href_clean,
                "href_raw": href_raw_clean,
                "markdown_url": markdown_link(display_text, href_clean),
                "text": display_text or None,
                "context": context,
                "timestamp": extracted_timestamp,
                "position": pos
            })
            pos += 1

    # Deduplicate
    seen, deduped = set(), []
    for it in items:
        key = (it["href"], (it["text"] or "").lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    return deduped

def extract_substack_any(html: str, base_url: str, client=None) -> List[dict]:
    soup = BeautifulSoup(html, "lxml")
    container = soup.select_one("div.body.markup")
    if not container:
        return []

    candidates = []
    for p in container.find_all("p", recursive=True):
        brs = p.find_all("br")
        links = p.find_all("a", href=True)
        if len(brs) >= 2 and len(links) >= 2:
            candidates.append((len(links) + len(brs), p))

    # If no candidates found with the <br> method, try fallback for older formats
    if not candidates:
        return _extract_substack_fallback(container, base_url, client)

    # Process ALL candidate paragraphs (not just the one with max score)
    # This handles gift guides and other multi-section episodes
    items, pos = [], 0
    for score, target_p in candidates:
        for seg in _segment_children_by_br(target_p):
            non_anchor_nodes = [n for n in seg if not (isinstance(n, Tag) and n.name == "a")]
            line_label = _text_content(non_anchor_nodes).strip().strip(":-—– ")
            if line_label == "@":
                line_label = ""

            anchors = []
            for n in seg:
                if isinstance(n, Tag) and n.name == "a" and n.get("href"):
                    anchors.append(n)
                elif isinstance(n, Tag):
                    anchors.extend(n.find_all("a", href=True))

            if not anchors:
                continue

            for a in anchors:
                href_raw = urljoin(base_url, a.get("data-href") or a.get("href"))
                if not _is_page_scheme(href_raw):
                    continue

                # Clean URLs that may have timestamps concatenated
                href_raw_clean, extracted_timestamp = _clean_url(href_raw)
                href_clean = resolve_redirectors(href_raw_clean, client=client)

                a_text = " ".join(a.stripped_strings) if a else ""
                display_text = a_text or line_label or href_clean

                line_full_text = _text_content(seg)
                context = line_full_text
                if display_text and display_text in context:
                    context = context.replace(display_text, "", 1).strip(" –—:;")
                if context == "":
                    context = None

                # Use extracted timestamp if context is empty
                if not context and extracted_timestamp:
                    context = extracted_timestamp

                items.append({
                    "href": href_clean,
                    "href_raw": href_raw_clean,
                    "markdown_url": markdown_link(display_text, href_clean),
                    "text": display_text or None,
                    "context": context,
                    "timestamp": extracted_timestamp,
                    "position": pos
                })
                pos += 1

    seen, deduped = set(), []
    for it in items:
        key = (it["href"], (it["text"] or "").lower())
        if key in seen:
            continue
        seen.add(key); deduped.append(it)
    return deduped

def nearest_related_container(soup: BeautifulSoup, override_selector: Optional[str] = None):
    if override_selector:
        nodes = soup.select(override_selector)
        if nodes:
            return nodes

    for h in soup.find_all(re.compile("^h[1-6]$")):
        t = h.get_text(strip=True) if h else ""
        if not t:
            continue
        if HEADING_RE.match(t):
            nxt = h.find_next(lambda tag: tag.name in ("ul","ol","div","section") and tag.find("a"))
            if nxt:
                items = nxt.find_all(["li","div","p"], recursive=True) or [nxt]
                return items

    for aside in soup.find_all(["aside","section","div"]):
        links = aside.find_all("a")
        if len(links) >= 3:
            return aside.find_all(["li","div","p"]) or links
    return []

def extract_items(nodes, base_url, client=None):
    results, pos = [], 0
    for n in nodes:
        a = n.find("a") if hasattr(n, "find") else None
        if not a or not a.get("href"):
            continue
        href_raw = urljoin(base_url, a.get("data-href") or a.get("href"))
        if not _is_page_scheme(href_raw):
            continue
        href_clean = resolve_redirectors(href_raw, client=client)
        a_text = " ".join(a.stripped_strings)
        container_text = " ".join(n.stripped_strings) if hasattr(n, "stripped_strings") else ""
        context = container_text if container_text and container_text != a_text else (a.get("title") or a.get("aria-label") or None)
        results.append({
            "href": href_clean,
            "href_raw": href_raw,
            "markdown_url": markdown_link(a_text or href_clean, href_clean),
            "text": a_text or None,
            "context": context,
            "timestamp": None,
            "position": pos
        })
        pos += 1

    seen = set(); deduped = []
    for it in results:
        key = (it["href"], (it["text"] or "").lower())
        if key in seen:
            continue
        seen.add(key); deduped.append(it)
    return deduped
