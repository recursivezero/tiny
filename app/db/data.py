import os
from typing import Any

# --- DEFENSIVE IMPORT ---
try:
    from pymongo import MongoClient

    MONGO_INSTALLED = True
except ImportError:
    # This allows the app to start even if 'pip install pymongo' wasn't run
    MONGO_INSTALLED = False

client: Any = None
db: Any = None
urls: Any = None
url_stats: Any = None


def connect_db():
    global client, db, urls, url_stats

    # 1. Check if the library is even there
    if not MONGO_INSTALLED:
        print("⚠️ pymongo is not installed. Running in NO-DB mode.")
        return False

    # 2. Check if the config is there
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = os.getenv("DATABASE_NAME", "tiny_url")

    if not MONGO_URI:
        print("⚠️ MONGO_URI missing. Running in NO-DB mode.")
        return False

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")

        db = client[DB_NAME]
        urls = db["urls"]
        url_stats = db["url_stats"]

        print(f"✅ MongoDB connected: '{DB_NAME}'")
        return True
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}. Running in NO-DB mode.")
        return False
