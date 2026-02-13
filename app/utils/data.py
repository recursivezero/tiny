# app/db/data.py

from typing import Any, Optional

# --- DEFENSIVE IMPORT ---
try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    MONGO_INSTALLED = True
except ImportError:
    MongoClient = None  # type: ignore

    class PyMongoError(Exception):
        pass

    MONGO_INSTALLED = False


from app.utils.config import MONGO_URI, MONGO_DB_NAME


class _DBState:
    client: Optional[Any] = None
    db: Optional[Any] = None
    collection: Optional[Any] = None
    available: bool = False


_state = _DBState()


def connect_db() -> bool:
    """
    Connect to MongoDB using config from env.
    Initializes shared collection.
    """
    if not MONGO_INSTALLED:
        print("⚠️ pymongo not installed. Running in NO-DB mode.")
        _state.client = None
        _state.db = None
        _state.collection = None
        _state.available = False
        return False

    mongo_uri = MONGO_URI
    mongo_db_name = MONGO_DB_NAME

    if not mongo_uri:
        print("⚠️ MONGO_URI not set. Running in NO-DB mode.")
        _state.client = None
        _state.db = None
        _state.collection = None
        _state.available = False
        return False

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        db = client[mongo_db_name]
        collection = db["urls"]

        _state.client = client
        _state.db = db
        _state.collection = collection
        _state.available = True

        print("✅ MongoDB connected")
        return True
    except PyMongoError:
        print("❌ MongoDB connection failed")
        _state.client = None
        _state.db = None
        _state.collection = None
        _state.available = False
        return False


def get_collection():
    """Return the shared Mongo collection or None."""
    return _state.collection
