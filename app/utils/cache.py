import time
from typing import TypedDict

CACHE_TTL = 900  # 15 minutes


class UrlCacheItem(TypedDict):
    url: str
    expires_at: float


class RevCacheItem(TypedDict):
    short_code: str
    expires_at: float


url_cache: dict[str, UrlCacheItem] = {}
rev_cache: dict[str, RevCacheItem] = {}


def get_from_cache(short_code: str) -> str | None:
    data = url_cache.get(short_code)

    if not data or data["expires_at"] < time.time():
        url_cache.pop(short_code, None)
        return None

    return data["url"]


def get_short_from_cache(original_url: str) -> str | None:
    data = rev_cache.get(original_url)

    if not data or data["expires_at"] < time.time():
        rev_cache.pop(original_url, None)
        return None

    return data["short_code"]


def set_cache_pair(short_code: str, original_url: str) -> None:
    expires_at = time.time() + CACHE_TTL

    url_cache[short_code] = {
        "url": original_url,
        "expires_at": expires_at,
    }

    rev_cache[original_url] = {
        "short_code": short_code,
        "expires_at": expires_at,
    }
