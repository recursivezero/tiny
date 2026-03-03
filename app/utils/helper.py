import string
import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Union

import validators
from app.utils.config import SHORT_CODE_LENGTH


def is_valid_url(url: str) -> bool:
    return bool(validators.url(url))


def sanitize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def generate_code(length: int = SHORT_CODE_LENGTH) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def format_date(value: Union[float, datetime, None]) -> str:
    """
    Formats both:
    - float/int epoch timestamps (from cache)
    - datetime objects (from DB)
    into: '24 Feb 2026, 03:59 PM' (IST)
    """
    if not value:
        return "Just now"

    # If cache timestamp (epoch seconds)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=ZoneInfo("Asia/Kolkata")).strftime(
            "%d %b %Y, %I:%M %p"
        )

    # If DB datetime
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %I:%M %p")

    return "Just now"
