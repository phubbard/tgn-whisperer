import re
from urllib.parse import urlparse
import urllib.robotparser as rp

MD_SPECIALS = re.compile(r"([\\`*_{}\[\]()#+\-.!|>])")

def md_escape(text: str) -> str:
    if not text:
        return ""
    return MD_SPECIALS.sub(r"\\\1", text)

def markdown_link(text: str, href: str) -> str:
    label = text or href
    return f"[{md_escape(label)}]({href})"

def domain(url: str) -> str:
    try:
        p = urlparse(url)
        return p.netloc.lower()
    except Exception:
        return ""

def can_fetch(url: str, ua: str = "Mozilla/5.0") -> bool:
    try:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        robots = f"{base}/robots.txt"
        r = rp.RobotFileParser()
        r.set_url(robots)
        r.read()
        return r.can_fetch(ua, url)
    except Exception:
        # If robots.txt is unavailable or malformed, proceed conservatively.
        return True
