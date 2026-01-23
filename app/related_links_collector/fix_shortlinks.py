"""
Utility to re-resolve unresolved shortlinks in an existing related.jsonl file.
This is useful after improving the resolver logic to fix previously failed resolutions.
"""
import json
import logging
from typing import Optional
import httpx
from .resolvers import expand_shortlink, SHORTENER_HOSTS
from urllib.parse import urlparse


def fix_shortlinks(jsonl_path: str, output_path: Optional[str] = None,
                  log: Optional[logging.Logger] = None) -> None:
    """
    Re-resolve unresolved shortlinks in a JSONL file.
    
    Args:
        jsonl_path: Path to the input JSONL file
        output_path: Path for output (defaults to overwriting input)
        log: Optional logger instance
    """
    log = log or logging.getLogger(__name__)
    output_path = output_path or jsonl_path
    
    records = []
    unresolved_count = 0
    resolved_count = 0
    
    # Read all records
    log.info("Reading records from %s", jsonl_path)
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))
    
    # Process records with HTTP client
    with httpx.Client(http2=True, headers={
        "User-Agent": "tgn-whisperer tgn.phfactor.net",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml"
    }, follow_redirects=True) as client:
        
        for rec in records:
            if rec.get('status') != 'ok':
                continue
            
            for link in rec.get('related', []):
                href = link.get('href', '')
                href_raw = link.get('href_raw', '')
                
                # Check if href is still a shortlink (unresolved)
                try:
                    host = urlparse(href).netloc.lower()
                    if host in SHORTENER_HOSTS:
                        unresolved_count += 1
                        log.info("Re-resolving: %s", href)
                        
                        # Attempt to resolve again
                        resolved = expand_shortlink(href, client)
                        
                        if resolved != href:
                            # Successfully resolved!
                            resolved_count += 1
                            link['href'] = resolved
                            log.info("  ✓ Resolved to: %s", resolved)
                        else:
                            log.warning("  ✗ Still unresolved: %s", href)
                except Exception as e:
                    log.error("Error processing %s: %s", href, e)
    
    # Write updated records
    log.info("Writing updated records to %s", output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    
    log.info("Summary: Found %d unresolved shortlinks, successfully resolved %d",
             unresolved_count, resolved_count)
    print(f"\nSummary:")
    print(f"  Found {unresolved_count} unresolved shortlinks")
    print(f"  Successfully resolved {resolved_count}")
    print(f"  Still unresolved: {unresolved_count - resolved_count}")


if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Usage: python fix_shortlinks.py <jsonl_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    fix_shortlinks(input_file, output_file)


