import string
import random
from datetime import timezone
import validators


def is_valid_url(url: str) -> bool:
    return bool(validators.url(url))


def sanitize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def generate_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def format_date(dt):
    if not dt:
        return "Just now (cache)"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.strftime("%d %b %Y, %I:%M %p")
