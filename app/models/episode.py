"""Episode model for Prefect workflows."""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Episode:
    """Data structure for a single podcast episode."""
    number: float = 0.0
    title: str = None
    subtitle: str = None
    mp3_url: str = None
    episode_url: str = None
    directory: str = None
    pub_date: str = None
    site_directory: str = None

    @property
    def episode_dir(self) -> Path:
        """Return Path object for episode directory."""
        return Path(self.directory) if self.directory else None

    @property
    def mp3_path(self) -> Path:
        """Return Path object for episode MP3 file."""
        if self.directory:
            return Path(self.directory) / "episode.mp3"
        return None

    @property
    def transcript_path(self) -> Path:
        """Return Path object for transcript JSON."""
        if self.directory:
            return Path(self.directory) / "episode-transcribed.json"
        return None

    @property
    def speaker_map_path(self) -> Path:
        """Return Path object for speaker map JSON."""
        if self.directory:
            return Path(self.directory) / "speaker-map.json"
        return None

    @property
    def markdown_path(self) -> Path:
        """Return Path object for episode markdown."""
        if self.directory:
            return Path(self.directory) / "episode.md"
        return None
