import re
import xml.etree.ElementTree as ET
from typing import Optional, Dict
import logging
import json
import os


def load_bitly_mapping(bitly_json_path: str, log: logging.Logger) -> Dict[str, str]:
    """Load bit.ly shortlink mappings from JSON file."""
    if not os.path.exists(bitly_json_path):
        log.warning("bitly.json not found at %s", bitly_json_path)
        return {}

    try:
        with open(bitly_json_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
            log.info("Loaded %d bit.ly mappings", len(mapping))
            return mapping
    except Exception as e:
        log.warning("Failed to load bitly.json: %s", e)
        return {}


def extract_urls_from_rss(rss_path: str, output_path: str,
                          log: Optional[logging.Logger] = None) -> None:
    """
    Extract show notes URLs from RSS feed's itunes:summary fields.
    Handles both direct Substack URLs and bit.ly shortlinks.

    Args:
        rss_path: Path to the RSS XML file
        output_path: Path to write the extracted URLs (one per line)
        log: Optional logger instance
    """
    log = log or logging.getLogger(__name__)

    log.info("Parsing RSS feed from %s", rss_path)

    # Load bit.ly mapping
    bitly_json_path = os.path.join(os.path.dirname(rss_path), 'bitly.json')
    bitly_mapping = load_bitly_mapping(bitly_json_path, log)

    # Parse the RSS file
    tree = ET.parse(rss_path)
    root = tree.getroot()

    # Define the iTunes namespace
    ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}

    # Extract URLs from itunes:summary fields
    urls = []
    shortlinks_expanded = 0

    for item in root.findall('.//item'):
        summary = item.find('itunes:summary', ns)
        if summary is not None and summary.text:
            # First try to find direct Substack URLs
            matches = re.findall(r'https://thegreynato\.substack\.com/p/[^\s<>\]]+', summary.text)
            if matches:
                urls.extend(matches)
            else:
                # Look for bit.ly shortlinks
                bitly_matches = re.findall(r'https?://bit\.ly/[^\s<>\]]+', summary.text)
                for shortlink in bitly_matches:
                    # Look up in mapping
                    expanded = bitly_mapping.get(shortlink)
                    if expanded:
                        # Ensure it has /p/ in the URL
                        if '/p/' not in expanded:
                            expanded = expanded.replace('thegreynato.substack.com/', 'thegreynato.substack.com/p/')
                        urls.append(expanded)
                        shortlinks_expanded += 1
                        log.debug("Expanded %s -> %s", shortlink, expanded)
                    else:
                        log.warning("No mapping found for shortlink: %s", shortlink)

    if shortlinks_expanded > 0:
        log.info("Expanded %d bit.ly shortlinks", shortlinks_expanded)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    # Write to output file
    log.info("Writing %d unique URLs to %s", len(unique_urls), output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        for url in unique_urls:
            f.write(url + '\n')
    
    log.info("Extracted %d unique URLs from the RSS feed", len(unique_urls))
    print(f"Extracted {len(unique_urls)} unique URLs from the RSS feed")
    print(f"Written to {output_path}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python extract_rss_urls.py <rss_file> <output_urls_file>")
        sys.exit(1)
    
    extract_urls_from_rss(sys.argv[1], sys.argv[2])


