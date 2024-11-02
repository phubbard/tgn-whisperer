from prefect import flow, task
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
from pathlib import Path
import time
from datetime import datetime
import json

@task(retries=3, retry_delay_seconds=5)
def fetch_page(url: str) -> str:
    """Fetch a page with rate limiting and retries"""
    time.sleep(1)  # Basic rate limiting
    response = httpx.get(url)
    response.raise_for_status()
    return response.text

@task
def parse_episode_list(html: str) -> List[Dict]:
    """Parse the TGN episode list page"""
    soup = BeautifulSoup(html, 'html.parser')
    episodes = []
    # Initial simple version focused on TGN
    for link in soup.select(".bs-sidebar a[href*='/episode/']"):
        episode_num = link['href'].split('/')[1]  # Gets NNN.0 format
        date_str = link.next_sibling.strip()
        episodes.append({
            'number': episode_num,
            'title': link.text,
            'date': date_str,
            'detail_url': f"https://tgn.phfactor.net/{episode_num}/episode/"
        })
    return episodes

@task
def fetch_episode_details(episode: Dict) -> Dict:
    """Fetch and parse the episode detail page"""
    html = fetch_page(episode['detail_url'])
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract show notes URL if available
    show_notes_link = soup.find('a', href=lambda h: h and 'substack.com' in h)
    if show_notes_link:
        episode['show_notes_url'] = show_notes_link['href']
    
    # Extract available content sections
    main_content = soup.find('div', {'role': 'main'})
    if main_content:
        # Basic content extraction - we'll enhance this later
        episode['synopsis'] = extract_section(main_content, 'Synopsis')
        episode['links'] = extract_links(main_content)
        episode['transcript'] = extract_section(main_content, 'Transcript')
    
    return episode

@task
def save_episode(episode: Dict, base_path: Path) -> None:
    """Save episode data in our standard format"""
    episode_path = base_path / f"episode_{episode['number']}.md"
    content = f"""# {episode['title']}

Published on {episode['date']}

## Synopsis
{episode.get('synopsis', 'No synopsis available')}

## Links
{format_links(episode.get('links', []))}

## Transcript
{episode.get('transcript', 'No transcript available')}
"""
    episode_path.write_text(content)

def extract_section(soup: BeautifulSoup, section_name: str) -> str:
    """Extract a section from the main content"""
    section = soup.find('h2', string=section_name)
    if section and section.find_next():
        return section.find_next().get_text().strip()
    return ''

def extract_links(soup: BeautifulSoup) -> List[Dict]:
    """Extract links from the content"""
    links = []
    links_section = soup.find('h2', string='Links')
    if links_section:
        for link in links_section.find_next('ul').find_all('a'):
            links.append({
                'text': link.get_text(),
                'url': link['href']
            })
    return links

def format_links(links: List[Dict]) -> str:
    """Format links for markdown output"""
    return '\n'.join([f"- [{link['text']}]({link['url']})" for link in links])

@flow(name="TGN Podcast Scraper")
def scrape_tgn_podcast(base_url: str = "https://tgn.phfactor.net/episodes/",
                      output_dir: str = "./content/tgn") -> None:
    """Main flow for scraping The Grey NATO podcast"""
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Fetch and parse episode list
    episode_list_html = fetch_page(base_url)
    episodes = parse_episode_list(episode_list_html)
    
    # Process each episode
    for episode in episodes:
        try:
            episode_with_details = fetch_episode_details(episode)
            save_episode(episode_with_details, output_path)
        except Exception as e:
            # Log error but continue processing
            print(f"Error processing episode {episode['number']}: {str(e)}")
    
    # Save metadata about the run
    metadata = {
        'last_run': datetime.now().isoformat(),
        'episodes_processed': len(episodes)
    }
    (output_path / 'status.json').write_text(json.dumps(metadata, indent=2))

if __name__ == "__main__":
    scrape_tgn_podcast()
