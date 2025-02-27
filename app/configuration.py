import re
from datastructures import Podcast

PODCAST_ROOT = 'podcasts'
SITE_ROOT = 'sites'

# Regex to pull the first number from a title - podcast number, in this case. Heuristic but works almost every time.
title_re = r'(\d+)'
title_matcher = re.compile(title_re)

# Grab any valid URL. Super complex, so classic cut-and-paste coding from StackOverflow.
# Of course. https://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url#3809435
url_rs = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
url_matcher = re.compile(url_rs)

