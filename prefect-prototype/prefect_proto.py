from prefect import flow, task
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
from pathlib import Path
import time
from datetime import datetime
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@task(retries=3, retry_delay_seconds=5)
def fetch_page(url: str) -> str:
    """Fetch a page with rate limiting and retries"""
    logger.debug(f"Fetching URL: {url}")
    time.sleep(1)  # Basic rate limiting
    response = httpx.get(url)
    response.raise_for_status()
    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response length: {len(response.text)}")
    return response.text

@task
def parse_episode_list(html: str) -> List[Dict]:
    """Parse the TGN episode list page"""
    logger.debug(f"Parsing HTML of length: {len(html)}")
    soup = BeautifulSoup(html, 'html.parser')
    
    # Debug the HTML structure
    sidebar = soup.select(".bs-sidebar")
    logger.debug(f"Found {len(sidebar)} sidebar elements")
    
    episode_links = soup.select(".bs-sidebar a[href*='/episode/']")
    logger.debug(f"Found {len(episode_links)} episode links")
    
    episodes = []
    for link in episode_links:
        try:
            episode_num = link['href'].split('/')[1]  # Gets NNN.0 format
            date_str = link.next_sibling.strip() if link.next_sibling else "No date found"
            logger.debug(f"Processing episode: {episode_num}, Title: {link.text}, Date: {date_str}")
            
            episodes.append({
                'number': episode_num,
                'title': link.text,
                'date': date_str,
                'detail_url': f"https://tgn.phfactor.net/{episode_num}/episode/"
            })
        except Exception as e:
            logger.error(f"Error processing episode link: {link}, Error: {str(e)}")
    
    logger.debug(f"Total episodes found: {len(episodes)}")
    return episodes

@task
def fetch_episode_details(episode: Dict) -> Dict:
    """Fetch and parse the episode detail page"""
    logger.debug(f"Fetching details for episode {episode['number']}")
    html = fetch_page(episode['detail_url'])
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract show notes URL if available
    show_notes_link = soup.find('a', href=lambda h: h and 'substack.com' in h)
    if show_notes_link:
        episode['show_notes_url'] = show_notes_link['href']
        logger.debug(f"Found show notes URL: {show_notes_link['href']}")
    
    # Extract available content sections
    main_content = soup.find('div', {'role': 'main'})
    if main_content:
        # Basic content extraction - we'll enhance this later
        episode['synopsis'] = extract_section(main_content, 'Synopsis')
        episode['links'] = extract_links(main_content)
        episode['transcript'] = extract_section(main_content, 'Transcript')
        logger.debug(f"Extracted content sections for episode {episode['number']}")
    else:
        logger.warning(f"No main content found for episode {episode['number']}")
    
    return episode

@flow(name="TGN Podcast Scraper")
def scrape_tgn_podcast(base_url: str = "https://tgn.phfactor.net/episodes/",
                      output_dir: str = "./content/tgn") -> None:
    """Main flow for scraping The Grey NATO podcast"""
    logger.info(f"Starting scrape of {base_url}")
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Fetch and parse episode list
    episode_list_html = fetch_page(base_url)
    episodes = parse_episode_list(episode_list_html)
    
    logger.info(f"Found {len(episodes)} episodes to process")
    
    # Process each episode
    for episode in episodes:
        try:
            logger.info(f"Processing episode {episode['number']}")
            episode_with_details = fetch_episode_details(episode)
            save_episode(episode_with_details, output_path)
        except Exception as e:
            logger.error(f"Error processing episode {episode['number']}: {str(e)}")
    
    # Save metadata about the run
    metadata = {
        'last_run': datetime.now().isoformat(),
        'episodes_processed': len(episodes)
    }
    (output_path / 'status.json').write_text(json.dumps(metadata, indent=2))
    logger.info("Scraping completed")

# Rest of the code remains the same...

if __name__ == "__main__":
    scrape_tgn_podcast()
