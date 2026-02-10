import time

CACHE_TTL = 900  # 15 minutes

url_cache = {}
rev_cache = {}


def get_from_cache(short_code: str):
    data = url_cache.get(short_code)
    if not data or data["expires_at"] < time.time():
        url_cache.pop(short_code, None)
        return None
    return data["url"]


def get_short_from_cache(original_url: str):
    data = rev_cache.get(original_url)
    if not data or data["expires_at"] < time.time():
        rev_cache.pop(original_url, None)
        return None
    return data["short_code"]


def set_cache_pair(short_code: str, original_url: str):
    expires_at = time.time() + CACHE_TTL
    url_cache[short_code] = {"url": original_url, "expires_at": expires_at}
    rev_cache[original_url] = {"short_code": short_code, "expires_at": expires_at}
