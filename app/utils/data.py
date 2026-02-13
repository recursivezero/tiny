from typing import Any, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    MONGO_INSTALLED = True
except ImportError:
    MongoClient = None
    PyMongoError = Exception
    MONGO_INSTALLED = False

from app.utils.config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION

client: Any = None
db: Any = None
collection: Any = None


def connect_db() -> bool:
    global client, db, collection

    if not MONGO_INSTALLED:
        print("⚠️ pymongo not installed. Running in NO-DB mode.")
        return False

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION]

        client.admin.command("ping")
        print("✅ MongoDB connected successfully")
        return True

    except Exception:
        print("❌ MongoDB connection failed")
        client = db = collection = None
        return False


def get_collection():
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
