from dataclasses import dataclass


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
    site_directory: str = None
    octoai: dict = None


# Sent as JSON to OctoAI
OctoAI = {
    "url": "",
    "task": "transcribe",
    "diarize": True,
    "min_speakers": 2,
    "prompt": "The following is a conversation including James and Jason"
}


# List of podcasts and their configuration is in configuration.py
@dataclass
class Podcast:
    name: str  # Unix style, short lowercase, used as a parent directory
    rss_url: str
    emails: list[str]  # Who to email with new episodes
    doc_base_url: str  # Used to create URLs for emails
