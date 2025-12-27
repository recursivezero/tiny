import re
import string
import random


def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r"^(https?:\/\/)" r"([\da-z\.-]+)\.([a-z\.]{2,6})" r"([\/\w \.-]*)*\/?$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url))


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
