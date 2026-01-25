"""Podcast model for Prefect workflows."""
from dataclasses import dataclass
from os import getenv


@dataclass
class Podcast:
    """Configuration for a podcast feed."""
    name: str  # Unix style, short lowercase, used as parent directory
    rss_url: str
    emails: list[str]  # Who to email with new episodes
    doc_base_url: str  # Used to create URLs for emails


# Podcast instances
def get_all_podcasts() -> list[Podcast]:
    """
    Return list of all configured podcasts.

    Episode numbers are automatically extracted from RSS feeds by rss_processor.py,
    which fills in missing itunes:episode tags chronologically.
    """
    # Get podcast configurations from environment variables with defaults
    tgn_emails = getenv('TGN_EMAILS', 'pfh@phfactor.net,lucafoglio@miller-companies.com').split(',')
    wcl_emails = getenv('WCL_EMAILS', 'pfh@phfactor.net,hello@watchclicker.com').split(',')
    hodinkee_emails = getenv('HODINKEE_EMAILS', 'pfh@phfactor.net').split(',')

    return [
        Podcast(
            name='tgn',
            rss_url='https://feeds.buzzsprout.com/2049759.rss',
            emails=tgn_emails,
            doc_base_url='https://tgn.phfactor.net'
        ),
        Podcast(
            name='wcl',
            rss_url='https://feed.podbean.com/the40and20podcast/feed.xml',
            emails=wcl_emails,
            doc_base_url='https://wcl.phfactor.net'
        ),
        Podcast(
            name='hodinkee',
            rss_url='https://feeds.simplecast.com/OzTmhziA',
            emails=hodinkee_emails,
            doc_base_url='https://hodinkee.phfactor.net'
        ),
    ]
