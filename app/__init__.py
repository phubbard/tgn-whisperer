import logging
from dataclasses import dataclass


# TODO
@dataclass
class EpisodeLink:
    description: str
    url: str


# Data structure for a single episode. Will be saved as JSON into the episodes' directory and used by Make.
@dataclass
class Episode:
    number: int = 0
    title: str = None
    subtitle: str = None
    mp3_url: str = None
    episode_url: str = None
    directory: str = None
    pub_date: str = None
    links: list[EpisodeLink] = None


@dataclass
class Podcast:
    name: str  # Unix style, short lowercase, used as a parent directory1
    last_notified: int  # TODO
    rss_url: str


