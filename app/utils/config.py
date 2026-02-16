import os

from dotenv import load_dotenv


def load_env():
    env = os.getenv("ENV", "development")
    file_map = {
        "production": ".env",
        "local": ".env.local",
        "development": ".env.development",
    }
    load_dotenv(file_map.get(env, ".env.development"), override=True)
    print(f"Environment selected: {env}")
    print(f"MODE value: {os.getenv('MODE')}")


# -------------------------
# Helpers
# -------------------------
def _get_bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes", "on")


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


# -------------------------
# App (constants + light env override)
# -------------------------
APP_NAME = "TinyURL"
MODE = os.getenv("MODE", "local")
DEBUG = MODE == "local"  # auto-debug in local

API_VERSION = os.getenv("API_VERSION", "v1")

# -------------------------
# Server
# -------------------------
HOST = "127.0.0.1"
PORT = _get_int("PORT", 8000)

# If DOMAIN not provided, derive from HOST + PORT
DOMAIN = os.getenv("DOMAIN", f"http://{HOST}:{PORT}")

# -------------------------
# Database
# -------------------------
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = "tiny_url"
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "urls")


# -------------------------
# Cache (constants)
# -------------------------
USE_CACHE = True
CACHE_TTL = 900  # 15 minutes
MAX_CACHE_SIZE = 10_000
MAX_RECENT_URLS = 20

# -------------------------
# Security / Sessions
# -------------------------
SESSION_SECRET = os.getenv("SESSION_SECRET", "super-secret-key")

# -------------------------
# Short URL (constants)
# -------------------------
SHORT_CODE_LENGTH = 6
MAX_URL_LENGTH = 2048
