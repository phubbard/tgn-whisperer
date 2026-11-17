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

# Hosts where show notes commonly link a bare @handle; used to label
# repaired anchors with the platform name.
SOCIAL_HOSTS = {
    "instagram.com": "Instagram",
    "soundcloud.com": "SoundCloud",
    "twitter.com": "Twitter",
    "x.com": "X",
    "youtube.com": "YouTube",
    "tiktok.com": "TikTok",
    "facebook.com": "Facebook",
}

HANDLE_TEXT = re.compile(r"@\s*([A-Za-z0-9._\-]*)")

def clean_handle_text(text: str, href: str) -> str:
    """Repair anchor text that is a bare or broken social @handle.

    Substack show notes sometimes split a handle across two anchors,
    leaving link text of just "@" or "@ handle" (seen in TGN episodes 8
    and 29). Rebuild a readable label from the text and URL, e.g.
    "@redbarcrew (Instagram)"; any other text passes through unchanged.
    """
    collapsed = " ".join((text or "").split())
    m = HANDLE_TEXT.fullmatch(collapsed)
    if not m:
        return text
    host = domain(href)
    if host.startswith("www."):
        host = host[4:]
    handle = m.group(1)
    if not handle:
        path_parts = [p for p in urlparse(href).path.split("/") if p]
        handle = path_parts[-1] if path_parts else host
    if not handle:
        return text
    label = f"@{handle}"
    platform = SOCIAL_HOSTS.get(host)
    if platform:
        label = f"{label} ({platform})"
    return label

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
