import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    MONGO_INSTALLED = True
except ImportError:
    MongoClient: Any = None  # type: ignore
    PyMongoError = Exception  # type: ignore
    MONGO_INSTALLED = False

from app.utils.config import MONGO_COLLECTION, MONGO_DB_NAME, MONGO_URI

# Configure logger
logger = logging.getLogger(__name__)

# MongoDB client and collection
client: Any = None
db: Any = None
collection: Any = None

# Connection state management
connection_state: str = "DISCONNECTED"  # DISCONNECTED, CONNECTING, CONNECTED, FAILED
last_connection_attempt: Optional[datetime] = None
connection_error: Optional[str] = None
health_check_task: Any = None


def connect_db(max_retries: int = 1) -> bool:
    """
    Connect to MongoDB with retry logic and exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (defaults to config value)

    Returns:
        True if connection successful, False otherwise
    """
    global client, db, collection, connection_state, last_connection_attempt, connection_error

    if not MONGO_INSTALLED:
        logger.error("PyMongo is not installed")
        connection_state = "FAILED"
        connection_error = "PyMongo not installed"
        return False

    if not MONGO_URI:
        logger.warning("⚠️ MONGO_URI not set. Running in NO-DB mode.")
        connection_state = "FAILED"
        connection_error = "MONGO_URI missing"
        return False

    from app.utils.config import (
        MONGO_TIMEOUT_MS,
        MONGO_SOCKET_TIMEOUT_MS,
        MONGO_MIN_POOL_SIZE,
        MONGO_MAX_POOL_SIZE,
    )

    connection_state = "CONNECTING"
    last_connection_attempt = datetime.utcnow()

    try:
        new_client: Any = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
            socketTimeoutMS=MONGO_SOCKET_TIMEOUT_MS,
            minPoolSize=MONGO_MIN_POOL_SIZE,
            maxPoolSize=MONGO_MAX_POOL_SIZE,
        )

        new_client.admin.command("ping")

        client = new_client
        db = new_client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION]

        connection_state = "CONNECTED"
        connection_error = None
        logger.info("✅ MongoDB connected")
        return True

    except Exception as e:
        logger.warning(f"⚠️ MongoDB not reachable. Running in NO-DB mode: {e}")
        connection_state = "FAILED"
        connection_error = str(e)
        client = db = collection = None
        return False


def get_collection() -> Optional[Any]:
    return collection


def is_connected() -> bool:
    return connection_state == "CONNECTED" and collection is not None


def get_connection_state() -> dict[str, Any]:
    """Return current connection state information."""
    return {
        "state": connection_state,
        "last_attempt": (
            last_connection_attempt.isoformat() if last_connection_attempt else None
        ),
        "error": connection_error,
        "connected": is_connected(),
    }


# ------------------------
# DB Operations (NO-OP SAFE)
# ------------------------


def find_by_original_url(original_url: str) -> Optional[dict]:
    if not is_connected():
        logger.warning("Database not connected, cannot find URL")
        return None
    try:
        return collection.find_one({"original_url": original_url})
    except PyMongoError as e:
        logger.error(f"DB error (find_by_original_url): {e}")
        _mark_failed(e)
        return None


def insert_url(short_code: str, original_url: str) -> bool:
    if not is_connected():
        return False
    try:
        collection.insert_one(
            {
                "short_code": short_code,
                "original_url": original_url,
                "created_at": datetime.utcnow(),
                "visit_count": 0,
            }
        )
        return True
    except PyMongoError as e:
        logger.error(f"DB error (insert_url): {e}")
        _mark_failed(e)
        return False


def delete_by_short_code(short_code: str) -> bool:
    if not is_connected():
        return False
    try:
        collection.delete_one({"short_code": short_code})
        return True
    except PyMongoError as e:
        logger.error(f"DB error (delete_by_short_code): {e}")
        _mark_failed(e)
        return False


def get_recent_urls(limit: int = 10) -> list[dict]:
    if not is_connected():
        return []
    try:
        return list(collection.find().sort("created_at", -1).limit(limit))
    except PyMongoError as e:
        logger.error(f"DB error (get_recent_urls): {e}")
        _mark_failed(e)
        return []


def increment_visit(short_code: str) -> Optional[dict]:
    if not is_connected():
        logger.warning("Database not connected, cannot increment visit")
        return None
    try:
        return collection.find_one_and_update(
            {"short_code": short_code},
            {"$inc": {"visit_count": 1}},
            return_document=True,
        )
    except PyMongoError as e:
        logger.error(f"DB error (increment_visit): {e}")
        _mark_failed(e)
        return None


def _mark_failed(e: Exception) -> None:
    global connection_state, connection_error, client, db, collection
    connection_state = "FAILED"
    connection_error = str(e)
    client = db = collection = None


# ------------------------
# Health Check (Background reconnect)
# ------------------------


async def health_check_loop() -> None:
    from app.utils.config import HEALTH_CHECK_INTERVAL_SECONDS

    logger.info("🫀 DB health check started")

    try:
        while True:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)

            if not is_connected():
                logger.info("🔁 DB disconnected. Retrying connection...")
                connect_db()
                continue

            try:
                if client:
                    client.admin.command("ping")
            except Exception as e:
                logger.error(f"❌ Health check failed: {e}")
                _mark_failed(e)

    except asyncio.CancelledError:
        logger.info("Health check loop cancelled")
        raise


def start_health_check() -> Any:
    """Start the background health check task."""
    global health_check_task

    health_check_task = asyncio.create_task(health_check_loop())
    logger.info("Health check task started")
    return health_check_task


async def stop_health_check() -> None:
    """Stop the background health check task."""
    global health_check_task

    if health_check_task is not None:
        logger.info("Stopping health check task...")
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            logger.info("Health check task stopped")
        health_check_task = None
