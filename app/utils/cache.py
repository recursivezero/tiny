import time
from typing import TypedDict

from app.utils.config import CACHE_TTL, MAX_RECENT_URLS


class UrlCacheItem(TypedDict):
    url: str
    expires_at: float


class RevCacheItem(TypedDict):
    short_code: str
    expires_at: float


# short_code -> original_url
url_cache: dict[str, UrlCacheItem] = {}

# original_url -> short_code
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

    return data["short_code"]


def set_cache_pair(short_code: str, original_url: str) -> None:
    expires_at = _now() + CACHE_TTL

    url_cache[short_code] = {
        "url": original_url,
        "expires_at": expires_at,
    }

    rev_cache[original_url] = {
        "short_code": short_code,
        "expires_at": expires_at,
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


# ---- Recent URLs Cache (Unique, Ordered, DB-shaped) ----

MAX_RECENT = MAX_RECENT_URLS
recent_urls: list[dict] = []  # same shape as DB docs


def add_recent(short_code: str, original_url: str) -> None:
    recent_urls[:] = [
        item
        for item in recent_urls
        if item["short_code"] != short_code and item["original_url"] != original_url
    ]

    recent_urls.insert(
        0,
        {
            "short_code": short_code,
            "original_url": original_url,
            "created_at": None,
            "visit_count": 0,
        },
    )

    del recent_urls[MAX_RECENT:]


def get_recent() -> list[dict]:
    return recent_urls
