# Per-podcast configs
from dataclasses import dataclass


@dataclass
class Podcast:
    name: str # Unix style, short lowercase, used as a parent directory1
    last_notified: int
    rss_url: str


tgn = Podcast('tgn', 254, 'https://feeds.buzzsprout.com/2049759.rss')
wcl = Podcast('wcl', 254, 'https://feed.podbean.com/the40and20podcast/feed.xml')

# Iterable to loop over
podcasts = [tgn, wcl]
