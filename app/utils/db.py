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
    Collection: Any  # type: ignore
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


def connect_db(max_retries: Optional[int] = None) -> bool:
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

    from app.utils.config import (
        MONGO_MAX_RETRIES,
        MONGO_INITIAL_RETRY_DELAY,
        MONGO_MAX_RETRY_DELAY,
        MONGO_TIMEOUT_MS,
        MONGO_SOCKET_TIMEOUT_MS,
        MONGO_MIN_POOL_SIZE,
        MONGO_MAX_POOL_SIZE,
    )
    import time

    if max_retries is None:
        max_retries = MONGO_MAX_RETRIES

    retry_delay = MONGO_INITIAL_RETRY_DELAY

    for attempt in range(1, max_retries + 1):
        connection_state = "CONNECTING"
        last_connection_attempt = datetime.utcnow()
        
        logger.info(f"Attempting to connect to MongoDB (attempt {attempt}/{max_retries})...")

        try:
            # Create MongoClient with timeout and pool settings
            new_client: Any = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
                socketTimeoutMS=MONGO_SOCKET_TIMEOUT_MS,
                minPoolSize=MONGO_MIN_POOL_SIZE,
                maxPoolSize=MONGO_MAX_POOL_SIZE,
            )
            
            # Validate connection with ping
            new_client.admin.command("ping")
            
            # Connection successful
            client = new_client
            db = new_client[MONGO_DB_NAME]
            collection = db[MONGO_COLLECTION]
            connection_state = "CONNECTED"
            connection_error = None
            
            logger.info("Successfully connected to MongoDB")
            return True

        except Exception as e:
            error_msg = f"Connection attempt {attempt} failed: {str(e)}"
            logger.warning(error_msg)
            connection_error = str(e)
            
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay:.1f} seconds...")
                time.sleep(retry_delay)
                # Exponential backoff: double delay, cap at max
                retry_delay = min(retry_delay * 2, MONGO_MAX_RETRY_DELAY)
            else:
                logger.error(f"Failed to connect after {max_retries} attempts")
                connection_state = "FAILED"
                client = db = collection = None

    return False


def get_collection() -> Optional[dict[str, Any]]:
    return collection


def get_connection_state() -> dict[str, Any]:
    """Return current connection state information."""
    return {
        "state": connection_state,
        "last_attempt": last_connection_attempt.isoformat() if last_connection_attempt else None,
        "error": connection_error,
        "connected": is_connected(),
    }


def is_connected() -> bool:
    """Check if database is currently connected."""
    return connection_state == "CONNECTED" and collection is not None


# ------------------------
# DB Operations
# ------------------------


def find_by_original_url(original_url: str) -> Optional[dict]:
    if not is_connected():
        logger.warning("Database not connected, cannot find URL")
        return None
    try:
        return collection.find_one({"original_url": original_url})
    except PyMongoError as e:
        logger.error(f"Error finding URL: {str(e)}")
        global connection_state, connection_error
        connection_state = "FAILED"
        connection_error = str(e)
        return None


def insert_url(short_code: str, original_url: str) -> bool:
    if not is_connected():
        logger.warning("Database not connected, cannot insert URL")
        return False
    try:
        collection.insert_one(
            {
                "short_code": short_code,
                "original_url": original_url,
                "created_at": __import__("datetime").datetime.utcnow(),
                "visit_count": 0,
            }
        )
        return True
    except PyMongoError as e:
        logger.error(f"Error inserting URL: {str(e)}")
        global connection_state, connection_error
        connection_state = "FAILED"
        connection_error = str(e)
        return False


def delete_by_short_code(short_code: str) -> bool:
    if not is_connected():
        logger.warning("Database not connected, cannot delete URL")
        return False
    try:
        collection.delete_one({"short_code": short_code})
        return True
    except PyMongoError as e:
        logger.error(f"Error deleting URL: {str(e)}")
        global connection_state, connection_error
        connection_state = "FAILED"
        connection_error = str(e)
        return False


def get_recent_urls(limit: int = 10) -> list[dict]:
    if not is_connected():
        logger.warning("Database not connected, cannot get recent URLs")
        return []
    try:
        return list(collection.find().sort("created_at", -1).limit(limit))
    except PyMongoError as e:
        logger.error(f"Error getting recent URLs: {str(e)}")
        global connection_state, connection_error
        connection_state = "FAILED"
        connection_error = str(e)
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
        logger.error(f"Error incrementing visit: {str(e)}")
        global connection_state, connection_error
        connection_state = "FAILED"
        connection_error = str(e)
        return None


# ------------------------
# Health Check
# ------------------------


async def health_check_loop() -> None:
    """Background task that periodically checks database connection health."""
    global connection_state, connection_error
    
    from app.utils.config import HEALTH_CHECK_INTERVAL_SECONDS
    
    logger.info("Health check loop started")
    
    try:
        while True:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
            
            logger.debug("Running health check...")
            
            # If disconnected, try to reconnect
            if not is_connected():
                logger.info("Database disconnected, attempting reconnection...")
                connect_db()
                continue
            
            # Validate active connection with ping
            try:
                if client is not None:
                    client.admin.command("ping")
                    logger.debug("Health check passed")
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                connection_state = "FAILED"
                connection_error = str(e)
                
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
