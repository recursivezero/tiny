import time
from typing import TypedDict

from app.utils.config import CACHE_TTL, MAX_RECENT_URLS


class UrlCacheItem(TypedDict):
    url: str
    expires_at: float
    visit_count: int


class RevCacheItem(TypedDict):
    short_code: str
    expires_at: float
    last_accessed: float


# short_code -> original_url
url_cache: dict[str, UrlCacheItem] = {}

# original_url -> short_code (+ metadata for recent tracking)
rev_cache: dict[str, RevCacheItem] = {}


def _now() -> float:
    return time.time()


def get_from_cache(short_code: str) -> str | None:
    data = url_cache.get(short_code)

    if not data:
        return None

    if data["expires_at"] < _now():
        url_cache.pop(short_code, None)
        return None

    return data["url"]


def get_short_from_cache(original_url: str) -> str | None:
    data = rev_cache.get(original_url)

    if not data:
        return None

    if data["expires_at"] < _now():
        rev_cache.pop(original_url, None)
        return None

    # Touch for recent tracking
    data["last_accessed"] = _now()

    return data["short_code"]


def set_cache_pair(short_code: str, original_url: str) -> None:
    now = _now()
    expires_at = now + CACHE_TTL

    url_cache[short_code] = {
    "url": original_url,
    "expires_at": expires_at,
    "visit_count": 0,
    }

    rev_cache[original_url] = {
        "short_code": short_code,
        "expires_at": expires_at,
        "last_accessed": now,
    }


def clear_cache() -> None:
    """
    Useful for tests or if DB goes down and you want to reset cache.
    """
    url_cache.clear()
    rev_cache.clear()


def cleanup_expired() -> None:
    """
    Optional: Manually remove expired cache entries.
    Can be called periodically (cron/background task).
    """
    now = _now()

    expired_short_codes = [
        key for key, value in url_cache.items() if value["expires_at"] < now
    ]
    for key in expired_short_codes:
        url_cache.pop(key, None)

    expired_urls = [
        key for key, value in rev_cache.items() if value["expires_at"] < now
    ]
    for key in expired_urls:
        rev_cache.pop(key, None)


# -----------------------
# Recent URLs (derived from rev_cache)
# -----------------------


def get_recent_from_cache(limit: int = MAX_RECENT_URLS) -> list[dict]:
    """
    Returns recent URLs based on cache activity (no duplicates, TTL-aware).
    Shape matches DB docs.
    """
    now = _now()

    items = [
    {
        "short_code": data["short_code"],
        "original_url": original_url,
        "visit_count": url_cache.get(data["short_code"], {}).get("visit_count", 0),
    }
    for original_url, data in rev_cache.items()
    if data["expires_at"] >= now
  ]

    items.sort(
        key=lambda x: rev_cache[x["original_url"]]["last_accessed"], reverse=True
    )

    return items[:limit]
