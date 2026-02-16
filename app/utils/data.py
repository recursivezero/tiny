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

client: Any = None
db: Any = None
collection: Any = None


def connect_db() -> bool:
    global client, db, collection

    if not MONGO_INSTALLED:
        return False

    try:
        # Create instance
        new_client: Any = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        new_client.admin.command("ping")
        client = new_client
        db = new_client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION]
        return True

    except Exception:
        client = db = collection = None
        return False

    return False


def get_collection() -> Optional[dict[str, Any]]:
    return collection


# ------------------------
# DB Operations
# ------------------------


def find_by_original_url(original_url: str) -> Optional[dict]:
    if collection is None:
        return None
    try:
        return collection.find_one({"original_url": original_url})
    except PyMongoError:
        return None


def insert_url(short_code: str, original_url: str) -> bool:
    if collection is None:
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
    except PyMongoError:
        return False


def delete_by_short_code(short_code: str) -> bool:
    if collection is None:
        return False
    try:
        collection.delete_one({"short_code": short_code})
        return True
    except PyMongoError:
        return False


def get_recent_urls(limit: int = 10) -> list[dict]:
    if collection is None:
        return []
    try:
        return list(collection.find().sort("created_at", -1).limit(limit))
    except PyMongoError:
        return []


def increment_visit(short_code: str) -> Optional[dict]:
    if collection is None:
        return None
    try:
        return collection.find_one_and_update(
            {"short_code": short_code},
            {"$inc": {"visit_count": 1}},
            return_document=True,
        )
    except PyMongoError:
        return None
