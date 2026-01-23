import re
from functools import lru_cache
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, unquote
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

MEDIUM_TRACKING_KEYS = {"source", "gi", "sk", "ref"}
MEDIUM_TRACKING_PREFIXES = ("utm_",)

def _strip_params(u, keys, prefixes):
    try:
        p = urlparse(u)
        qs = parse_qs(p.query, keep_blank_values=True)
        clean = {k: v for k, v in qs.items()
                 if k not in keys and not any(k.startswith(pref) for pref in prefixes)}
        new_q = urlencode({k: (vals[0] if len(vals)==1 else vals) for k, vals in clean.items()}, doseq=True)
        return urlunparse(p._replace(query=new_q))
    except Exception:
        return u

def resolve_medium_redirect(u: str, client=None) -> str:
    try:
        p = urlparse(u)
        host = p.netloc.lower()
        path = p.path or "/"
        qs = parse_qs(p.query)

        if path.startswith("/r/") and "url" in qs:
            return unquote(qs["url"][0])

        if path.startswith("/m/global-identity-2") and "redirectUrl" in qs:
            return unquote(qs["redirectUrl"][0])

        if host.endswith("medium.com") and "redirect" in qs and qs["redirect"]:
            return unquote(qs["redirect"][0])

        if host == "link.medium.com" and client is not None:
            try:
                r = client.head(u, follow_redirects=True, timeout=10)
                return str(r.url)
            except Exception:
                try:
                    r = client.get(u, follow_redirects=True, timeout=12, headers={"Range": "bytes=0-0"})
                    return str(r.url)
                except Exception:
                    return u

        if host.endswith("medium.com"):
            return _strip_params(u, MEDIUM_TRACKING_KEYS, MEDIUM_TRACKING_PREFIXES)

        if "source" in qs and re.search(r"^/p/[0-9a-f]+", path):
            return _strip_params(u, MEDIUM_TRACKING_KEYS, MEDIUM_TRACKING_PREFIXES)

        return u
    except Exception:
        return u

SHORTENER_HOSTS = {
    "bit.ly","amzn.to","imdb.to","t.co","buff.ly","ow.ly","tinyurl.com",
    "goo.gl","lnkd.in","rebrand.ly","is.gd","trib.al","shorturl.at","s.co",
    "ift.tt","fb.me","cl.ly","rb.gy","soo.gd","shor.by","cutt.ly","v.gd",
    "youtu.be"
}

UTM_PREFIXES = ("utm_",)
STRIP_KEYS = {"ref", "ref_src", "feature", "tag", "ascsubtag", "linkCode", "creative",
              "creativeASIN", "camp", "subscriptionId", "pd_rd_w", "pd_rd_r",
              "pf_rd_p","pf_rd_r","psc","keywords","crid","smid","qid"}

def strip_tracking(u: str) -> str:
    return _strip_params(u, STRIP_KEYS, UTM_PREFIXES)

@lru_cache(maxsize=4096)
def _cache_get(url: str) -> str:
    return url

class TransientResolveError(Exception):
    """Temporary error that should be retried."""
    pass

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(TransientResolveError)
)
def _resolve_with_retry(u: str, client) -> str:
    """Attempt to resolve a shortlink with retries on transient errors."""
    try:
        r = client.head(u, follow_redirects=True, timeout=12)
        if r.status_code in (429, 503, 504):
            raise TransientResolveError(f"HTTP {r.status_code}")
        return str(r.url)
    except httpx.TimeoutException:
        raise TransientResolveError("Timeout")
    except httpx.ConnectError:
        raise TransientResolveError("Connection error")
    except TransientResolveError:
        raise
    except Exception:
        # Try GET as fallback
        try:
            r = client.get(u, follow_redirects=True, timeout=15, headers={"Range": "bytes=0-0"})
            if r.status_code in (429, 503, 504):
                raise TransientResolveError(f"HTTP {r.status_code}")
            return str(r.url)
        except httpx.TimeoutException:
            raise TransientResolveError("Timeout on GET")
        except TransientResolveError:
            raise
        except Exception:
            raise

def expand_shortlink(u: str, client) -> str:
    try:
        host = urlparse(u).netloc.lower()
        if host not in SHORTENER_HOSTS:
            return u
        cached = _cache_get(u)
        if cached != u:
            return cached

        dest = _resolve_with_retry(u, client)

        # Cache hack: clear and then seed both keys so subsequent calls are O(1)
        _cache_get.cache_clear()
        _cache_get(u)
        _cache_get(dest)
        return dest
    except Exception:
        # If all retries fail, return original URL
        return u

def resolve_redirectors(u: str, client=None) -> str:
    cleaned = resolve_medium_redirect(u, client=client)
    if client is not None:
        cleaned = expand_shortlink(cleaned, client)
    return strip_tracking(cleaned)
