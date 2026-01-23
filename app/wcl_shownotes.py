#!/usr/bin/env python3
"""
Extract show notes from WCL RSS feed and generate shownotes.md
"""

import re
import xmltodict
from datetime import datetime
from html import unescape
from pathlib import Path
from loguru import logger as log


def extract_links_from_html(html_content):
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


def parse_wcl_feed(feed_path):
    """Parse WCL RSS feed and extract episode data with links."""
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

        links = extract_links_from_html(content)

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


def generate_shownotes_md(episodes, output_path):
    """Generate shownotes.md file in TGN format."""

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
    log.info(f"Wrote shownotes to {output_path}")
    log.info(f"Total: {total_links} links from {episodes_with_links} episodes")


if __name__ == '__main__':
    feed_path = Path('../wcl_feed.rss')
    output_path = Path('../sites/wcl/docs/shownotes.md')

    log.info(f"Parsing WCL RSS feed: {feed_path}")
    episodes = parse_wcl_feed(feed_path)

    log.info(f"Found {len(episodes)} episodes")
    generate_shownotes_md(episodes, output_path)
