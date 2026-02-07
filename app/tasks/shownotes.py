"""Prefect tasks for generating podcast shownotes."""
import re
import xmltodict
from datetime import datetime
from html import unescape
from pathlib import Path
from prefect import task
from prefect.cache_policies import INPUTS
from utils.logging import get_logger

# Import TGN-specific functions from related_links_collector
from related_links_collector.extract_rss_urls import extract_urls_from_rss
from related_links_collector.scrape import run as scrape_run
from related_links_collector.generate_markdown import generate_markdown


@task(
    name="generate-tgn-shownotes",
    retries=2,
    retry_delay_seconds=60,
    cache_policy=INPUTS,
    log_prints=True
)
def generate_tgn_shownotes(rss_path: Path, output_path: Path) -> Path:
    """
    Generate TGN shownotes by scraping Substack episode pages.

    Workflow:
    1. Extract episode URLs from RSS feed
    2. Scrape related links from each episode page
    3. Generate markdown document

    Args:
        rss_path: Path to TGN RSS feed
        output_path: Path where shownotes.md should be written

    Returns:
        Path to generated shownotes file
    """
    log = get_logger()
    log.info("Generating TGN shownotes from Substack episode pages")

    # Set up paths for cache and working files
    # IMPORTANT: tgn_related.jsonl is a PERMANENT CACHE - never delete it!
    # Scraping is expensive (~1-2 hours for 361 episodes) and old episodes never change.
    # The scraper automatically skips URLs already in this file.
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)

    urls_file = data_dir / 'tgn_urls.txt'  # Working file: episode URLs from RSS (regenerated each run)
    related_file = data_dir / 'tgn_related.jsonl'  # PERMANENT CACHE: scraped episode data (append-only)
    exceptions_file = data_dir / 'tgn_exceptions.jsonl'  # Working file: scraping errors

    # Check that RSS feed exists
    if not rss_path.exists():
        raise FileNotFoundError(f"RSS feed not found: {rss_path}")

    # Step 1: Extract episode URLs from RSS feed
    log.info("Step 1: Extracting episode URLs from RSS feed")
    extract_urls_from_rss(str(rss_path), str(urls_file), log=log)

    # Step 2: Scrape related links from episode pages
    log.info("Step 2: Scraping related links from episode pages")
    scrape_run(
        urls_path=str(urls_file),
        out_path=str(related_file),
        exceptions_path=str(exceptions_file),
        overrides_path=None,
        rate=1.2,
        log=log
    )

    # Step 3: Generate markdown document
    log.info("Step 3: Generating markdown document")
    generate_markdown(
        rss_path=str(rss_path),
        jsonl_path=str(related_file),
        output_path=str(output_path),
        log=log
    )

    log.info(f"TGN shownotes generated: {output_path}")
    return output_path


def _extract_links_from_html(html_content: str) -> list[dict]:
    """Extract links from HTML content, filtering out boilerplate."""
    # Unescape HTML entities
    content = unescape(html_content)

    # Find all <a href='...'> tags
    link_pattern = r"<a\s+href=['\"]([^'\"]+)['\"]>([^<]+)</a>"
    matches = re.findall(link_pattern, content, re.IGNORECASE)

    # Boilerplate domains/URLs to skip
    skip_patterns = [
        'watchclicker.com',
        'patreon.com',
        'instagram.com',
        'incompetch.com',
        'creativecommons.org',
        'gate.sc',
        'affrontography.com',
        'fosterwatches.com',
        'escapementmedia.com',
    ]

    links = []
    for url, text in matches:
        # Skip if URL contains any skip patterns
        if any(pattern in url.lower() for pattern in skip_patterns):
            continue

        # Skip empty or very short text
        if len(text.strip()) < 3:
            continue

        links.append({'url': url, 'text': text.strip()})

    return links


def _parse_wcl_feed(feed_path: Path, log=None) -> list[dict]:
    """Parse WCL RSS feed and extract episode data with links."""
    if log is None:
        log = get_logger()

    with open(feed_path, 'r', encoding='utf-8') as f:
        feed_data = xmltodict.parse(f.read())

    episodes = []
    items = feed_data['rss']['channel']['item']

    for item in items:
        # Extract basic episode info
        title = item.get('title', 'Unknown')
        link = item.get('link', '')
        pub_date = item.get('pubDate', '')

        # Get episode number from itunes:episode tag
        ep_num = item.get('itunes:episode')
        if not ep_num:
            log.warning(f"No episode number for: {title}")
            continue

        # Extract links from description or content:encoded
        description = item.get('description', '')
        content = item.get('content:encoded', description)

        links = _extract_links_from_html(content)

        # Parse publication date
        try:
            pub_datetime = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
            pub_date_formatted = pub_datetime.strftime('%B %d, %Y at %I:%M %p')
        except:
            pub_date_formatted = pub_date

        episodes.append({
            'number': float(ep_num),
            'title': title,
            'link': link,
            'pub_date': pub_date_formatted,
            'links': links
        })

    # Sort by episode number descending (newest first)
    episodes.sort(key=lambda x: x['number'], reverse=True)

    return episodes


def _generate_wcl_markdown(episodes: list[dict], output_path: Path, log=None):
    """Generate shownotes.md file in TGN format."""
    if log is None:
        log = get_logger()

    # Calculate statistics
    total_links = sum(len(ep['links']) for ep in episodes)
    episodes_with_links = sum(1 for ep in episodes if len(ep['links']) > 0)
    episodes_without_links = len(episodes) - episodes_with_links
    avg_links = total_links / episodes_with_links if episodes_with_links > 0 else 0

    # Generate markdown
    lines = []
    lines.append("# 40 and 20 - Show Notes Collection")
    lines.append("")
    lines.append(f"Generated on {datetime.now().strftime('%B %d, %Y')}")
    lines.append("")
    lines.append(f"**{total_links} total links from {episodes_with_links} episodes "
                 f"(out of {len(episodes)} episodes scraped, {episodes_without_links} without any links), "
                 f"averaging {avg_links:.1f} per episode.**")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Add each episode
    for ep in episodes:
        lines.append(f"## [{ep['title']}]({ep['link']})")
        lines.append("")
        lines.append(f"**Published:** {ep['pub_date']}")
        lines.append("")

        if ep['links']:
            lines.append(f"**Related Links ({len(ep['links'])}):**")
            lines.append("")
            for link in ep['links']:
                lines.append(f"- [{link['text']}]({link['url']})")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Write to file
    output_path.write_text('\n'.join(lines))
    log.info(f"Wrote WCL shownotes to {output_path}")
    log.info(f"Total: {total_links} links from {episodes_with_links} episodes")


@task(
    name="generate-wcl-shownotes",
    retries=2,
    retry_delay_seconds=60,
    cache_policy=INPUTS,
    log_prints=True
)
def generate_wcl_shownotes(rss_path: Path, output_path: Path) -> Path:
    """
    Generate WCL shownotes by extracting links from RSS feed HTML.

    Args:
        rss_path: Path to WCL RSS feed
        output_path: Path where shownotes.md should be written

    Returns:
        Path to generated shownotes file
    """
    log = get_logger()
    log.info("Generating WCL shownotes from RSS feed HTML")

    if not rss_path.exists():
        raise FileNotFoundError(f"RSS feed not found: {rss_path}")

    # Parse feed and extract links
    episodes = _parse_wcl_feed(rss_path, log)
    log.info(f"Found {len(episodes)} episodes")

    # Generate markdown
    _generate_wcl_markdown(episodes, output_path, log)

    log.info(f"WCL shownotes generated: {output_path}")
    return output_path


@task(
    name="generate-hodinkee-shownotes",
    log_prints=True
)
def generate_hodinkee_shownotes(rss_path: Path, output_path: Path) -> Path:
    """
    Generate Hodinkee shownotes (placeholder - not yet implemented).

    Args:
        rss_path: Path to Hodinkee RSS feed
        output_path: Path where shownotes.md should be written

    Returns:
        Path to generated shownotes file (or None if not implemented)
    """
    log = get_logger()
    log.warning("Hodinkee shownotes generation not yet implemented")
    return None
