import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
import logging


def parse_rss_episodes(rss_path: str) -> dict:
    """Parse RSS feed and extract episode metadata."""
    tree = ET.parse(rss_path)
    root = tree.getroot()
    
    ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
    
    episodes = {}
    for item in root.findall('.//item'):
        title_elem = item.find('title')
        summary_elem = item.find('itunes:summary', ns)
        pubdate_elem = item.find('pubDate')
        
        if summary_elem is not None and summary_elem.text:
            matches = re.findall(r'https://thegreynato\.substack\.com/p/[^\s<>\]]+', summary_elem.text)
            if matches:
                url = matches[0]
                
                # Parse the publication date
                pubdate = pubdate_elem.text if pubdate_elem is not None else "Unknown date"
                if pubdate != "Unknown date":
                    try:
                        # Parse RFC 2822 format: Thu, 23 Oct 2025 06:00:00 -0400
                        dt = datetime.strptime(pubdate.rsplit(' ', 1)[0], '%a, %d %b %Y %H:%M:%S')
                        formatted_date = dt.strftime('%B %d, %Y at %I:%M %p')
                    except Exception:
                        formatted_date = pubdate
                else:
                    formatted_date = pubdate
                
                episodes[url] = {
                    'title': title_elem.text if title_elem is not None else 'Unknown Title',
                    'pubdate': formatted_date,
                    'url': url
                }
    
    return episodes


def load_related_links(jsonl_path: str) -> dict:
    """Load related links from JSONL file."""
    related_links = {}
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            url = rec.get('source_url')
            if rec.get('status') == 'ok':
                related_links[url] = rec.get('related', [])
    
    return related_links


def generate_markdown(rss_path: str, jsonl_path: str, output_path: str,
                     log: Optional[logging.Logger] = None) -> None:
    """Generate a markdown file combining RSS metadata with related links."""
    log = log or logging.getLogger(__name__)
    
    log.info("Parsing RSS feed from %s", rss_path)
    episodes = parse_rss_episodes(rss_path)
    
    log.info("Loading related links from %s", jsonl_path)
    related_links = load_related_links(jsonl_path)
    
    log.info("Generating markdown file at %s", output_path)

    # Calculate statistics from ALL scraped episodes (not just those in RSS)
    total_links = 0
    episodes_with_links = 0
    episodes_without_links = 0
    total_episodes_scraped = len(related_links)

    for url, links in related_links.items():
        if links:
            total_links += len(links)
            episodes_with_links += 1
        else:
            episodes_without_links += 1

    avg_links = total_links / episodes_with_links if episodes_with_links > 0 else 0

    with open(output_path, 'w', encoding='utf-8') as out:
        out.write('# The Grey NATO - Show Notes Collection\n\n')
        out.write(f'Generated on {datetime.now().strftime("%B %d, %Y")}\n\n')
        out.write(f'**{total_links} total links from {episodes_with_links} episodes (out of {total_episodes_scraped} episodes scraped, {episodes_without_links} without any links), averaging {avg_links:.1f} per episode.**\n\n')
        out.write('---\n\n')

        # Iterate through episodes in the order they appear in RSS (newest first)
        episodes_processed = 0
        for url, metadata in episodes.items():
            if url in related_links:
                out.write(f'## [{metadata["title"]}]({url})\n\n')
                out.write(f'**Published:** {metadata["pubdate"]}\n\n')
                
                links = related_links[url]
                if links:
                    out.write(f'**Related Links ({len(links)}):**\n\n')
                    for link in links:
                        text = link.get('text', '').strip()
                        href = link.get('href', '').strip()
                        context = link.get('context') or ''
                        context = context.strip() if context else ''
                        
                        # If text is just a shortlink, prefer context or href as display text
                        if text and any(shortener in text.lower() for shortener in 
                                       ['bit.ly', 'amzn.to', 'youtu.be', 'goo.gl', 't.co', 'tinyurl.com']):
                            if context:
                                text = context
                            else:
                                text = href
                        
                        if text and href:
                            out.write(f'- [{text}]({href})\n')
                        elif href:
                            out.write(f'- {href}\n')
                else:
                    out.write('*No related links found*\n')
                
                out.write('\n---\n\n')
                episodes_processed += 1
    
    log.info("Generated %s with %d episodes", output_path, episodes_processed)
    print(f"Generated {output_path} with {episodes_processed} episodes")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python generate_markdown.py <rss_file> <jsonl_file> <output_md>")
        sys.exit(1)
    
    generate_markdown(sys.argv[1], sys.argv[2], sys.argv[3])

