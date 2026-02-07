from os import getenv

INPUT_FILE = "whisper-output.json"
SPEAKER_MAPFILE = "speaker-map.json"
SYNOPSIS_FILE = "synopsis.txt"

EPISODE_TRANSCRIBED_JSON = 'episode-transcribed.json'
SPEAKER_MAP = 'speaker-map.json'

UNKNOWN = 'Unknown'
NEW_NAME = '- New name'

from pathlib import Path

# Use absolute path to avoid issues when running from different directories
SITE_ROOT = str(Path(__file__).parent.parent / 'sites')
system_admin = getenv('SYSTEM_ADMIN_EMAIL', 'tgn-whisperer@phfactor.net')

# SMTP Configuration
SMTP_SERVER = getenv('SMTP_SERVER', 'smtp.fastmail.com')
SMTP_PORT = int(getenv('SMTP_PORT', '465'))
SMTP_USERNAME = getenv('SMTP_USERNAME', 'pfh@phfactor.net')
CONTACT_EMAIL = getenv('CONTACT_EMAIL', 'pfh@phfactor.net')

# Transcription API Configuration
TRANSCRIPTION_API_BASE_URL = getenv('TRANSCRIPTION_API_BASE_URL', 'http://axiom.phfactor.net:5051')

# Deployment Configuration
DEPLOY_BASE_PATH = getenv('DEPLOY_BASE_PATH', '/usr/local/www')

# Claude/Anthropic Configuration
CLAUDE_MODEL = getenv('CLAUDE_MODEL', 'claude-sonnet-4-5')
CLAUDE_MAX_TOKENS = int(getenv('CLAUDE_MAX_TOKENS', '2000'))

# Default URLs
DEFAULT_PODCAST_URL = getenv('DEFAULT_PODCAST_URL', 'https://thegreynato.com/')

# HTTP User Agent
HTTP_USER_AGENT = getenv('HTTP_USER_AGENT', 'tgn-whisperer https://github.com/phubbard/tgn-whisperer/')


def format_episode_number(episode_number: float) -> str:
    """
    Format episode number for directory/file naming.

    TGN uses hand-authored episode numbers. Integer episodes use no .0 suffix,
    fractional episodes (Q&As, special episodes) keep the decimal.

    Args:
        episode_number: Episode number as float

    Returns:
        Formatted string: "363" for integers, "14.5" for fractional
    """
    if episode_number == int(episode_number):
        return str(int(episode_number))
    return str(episode_number)
