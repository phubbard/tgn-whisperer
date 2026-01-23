"""Podcast model for Prefect workflows."""
from dataclasses import dataclass
from typing import Callable


@dataclass
class Podcast:
    """Configuration for a podcast feed."""
    name: str  # Unix style, short lowercase, used as parent directory
    rss_url: str
    emails: list[str]  # Who to email with new episodes
    doc_base_url: str  # Used to create URLs for emails
    number_extractor_function: Callable  # Function to extract episode numbers


# Podcast instances
def get_all_podcasts() -> list[Podcast]:
    """Return list of all configured podcasts."""
    # Import here to avoid circular dependency
    # Note: This function is from process.py but we'll use a dummy for now
    # since we're extracting episode numbers directly from RSS in tasks/rss.py
    def episode_number_from_rss(entry):
        """Extract episode number from RSS entry."""
        meta_entry = entry.get('itunes:episode', None)
        if meta_entry:
            return float(meta_entry)
        return None

    return [
        Podcast(
            name='tgn',
            rss_url='https://feeds.buzzsprout.com/2049759.rss',
            emails=['pfh@phfactor.net', 'lucafoglio@miller-companies.com'],
            doc_base_url='https://tgn.phfactor.net',
            number_extractor_function=episode_number_from_rss
        ),
        Podcast(
            name='wcl',
            rss_url='https://feed.podbean.com/the40and20podcast/feed.xml',
            emails=['pfh@phfactor.net', 'hello@watchclicker.com'],
            doc_base_url='https://wcl.phfactor.net',
            number_extractor_function=episode_number_from_rss
        ),
        Podcast(
            name='hodinkee',
            rss_url='https://feeds.simplecast.com/OzTmhziA',
            emails=['pfh@phfactor.net'],
            doc_base_url='https://hodinkee.phfactor.net',
            number_extractor_function=episode_number_from_rss
        ),
    ]
