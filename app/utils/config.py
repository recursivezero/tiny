import os

# -------------------------
# Helpers
# -------------------------


from app.utils.config_env import load_env  # noqa: F401

load_env()


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

# Connection timeouts (in milliseconds)
MONGO_TIMEOUT_MS = _get_int("MONGO_TIMEOUT_MS", 10000)
MONGO_SOCKET_TIMEOUT_MS = _get_int("MONGO_SOCKET_TIMEOUT_MS", 20000)

# Connection pool settings
MONGO_MIN_POOL_SIZE = _get_int("MONGO_MIN_POOL_SIZE", 5)
MONGO_MAX_POOL_SIZE = _get_int("MONGO_MAX_POOL_SIZE", 50)

# Retry configuration
MONGO_MAX_RETRIES = _get_int("MONGO_MAX_RETRIES", 10)
MONGO_INITIAL_RETRY_DELAY = 1.0
MONGO_MAX_RETRY_DELAY = 30.0

# Health check interval (in seconds)
HEALTH_CHECK_INTERVAL_SECONDS = _get_int("HEALTH_CHECK_INTERVAL_SECONDS", 30)


# -------------------------
# Cache (constants)
# -------------------------
USE_CACHE = True
CACHE_TTL = 900  # 15 minutes
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
