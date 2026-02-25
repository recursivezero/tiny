import time
from typing import TypedDict
from datetime import datetime
from zoneinfo import ZoneInfo
from app.utils.config import CACHE_TTL, MAX_RECENT_URLS


class UrlCacheItem(TypedDict):
    url: str
    expires_at: float


class RevCacheItem(TypedDict):
    short_code: str
    expires_at: float
    created_at: float
    last_accessed: float


# -----------------------
# Performance caches (TTL)
# -----------------------

# short_code -> original_url
url_cache: dict[str, UrlCacheItem] = {}

# original_url -> short_code (+ metadata for recent tracking)
rev_cache: dict[str, RevCacheItem] = {}

# short_code -> visit_count (temporary, in-memory)
visit_cache: dict[str, int] = {}


def _now() -> float:
    return time.time()


# -----------------------
# Core cache operations
# -----------------------


def set_cache_pair(short_code: str, original_url: str) -> None:
    now = _now()
    expires_at = now + CACHE_TTL

    url_cache[short_code] = {
        "url": original_url,
        "expires_at": expires_at,
    }

    rev_cache[original_url] = {
        "short_code": short_code,
        "expires_at": expires_at,
        "created_at": now,
        "last_accessed": now,
    }


def increment_visit_cache(short_code: str) -> None:
    visit_cache[short_code] = visit_cache.get(short_code, 0) + 1


def get_from_cache(short_code: str) -> str | None:
    data = url_cache.get(short_code)

    if not data:
        return None

    if data["expires_at"] < _now():
        url_cache.pop(short_code, None)
        _remove_recent_if_exists(short_code)
        return None

    return data["url"]


def get_short_from_cache(original_url: str) -> str | None:
    data = rev_cache.get(original_url)

    if not data:
        return None

    if data["expires_at"] < _now():
        rev_cache.pop(original_url, None)
        return None

    data["last_accessed"] = _now()
    return data["short_code"]


def get_recent_from_cache(limit: int = MAX_RECENT_URLS) -> list[dict]:
    now = _now()

    valid_items = [
        {
            "short_code": data["short_code"],
            "original_url": original_url,
            "created_at": data["created_at"],
        }
        for original_url, data in rev_cache.items()
        if data["expires_at"] >= now
    ]

    valid_items.sort(key=lambda x: x["created_at"], reverse=True)
    return valid_items[:limit]


def cleanup_expired() -> None:
    now = _now()

    expired_short_codes = [
        short_code for short_code, data in url_cache.items() if data["expires_at"] < now
    ]

    for short_code in expired_short_codes:
        url_cache.pop(short_code, None)
        _remove_recent_if_exists(short_code)

    expired_original_urls = [
        original_url
        for original_url, data in rev_cache.items()
        if data["expires_at"] < now
    ]

    for original_url in expired_original_urls:
        rev_cache.pop(original_url, None)


def clear_cache() -> None:
    url_cache.clear()
    rev_cache.clear()


def _remove_recent_if_exists(short_code: str) -> None:
    to_delete = None

    for original_url, data in rev_cache.items():
        if data["short_code"] == short_code:
            to_delete = original_url
            break

    if to_delete:
        rev_cache.pop(to_delete, None)


# -----------------------
# UI helpers
# -----------------------


def list_cache_clean() -> dict:
    """
    Clean UI-friendly cache view (TTL-aware, no debug noise).
    """
    now = _now()

    items = [
        {
            "short_code": data["short_code"],
            "original_url": original_url,
            "created_at": datetime.fromtimestamp(
                data["created_at"], tz=ZoneInfo("Asia/Kolkata")
            ).strftime("%d %b %Y, %I:%M %p"),
        }
        for original_url, data in rev_cache.items()
        if data["expires_at"] >= now
    ]

    return {
        "count": len(items),
        "items": items,
        "MAX_RECENT_URLS": MAX_RECENT_URLS,
        "CACHE_TTL": CACHE_TTL,
    }
