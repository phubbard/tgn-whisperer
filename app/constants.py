
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
system_admin = 'tgn-whisperer@phfactor.net'
