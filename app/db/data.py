import os
from typing import Any

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app.utils.config import load_env

load_env()  # explicit call

client: Any = None
db = None
urls = None
url_stats = None


def connect_db():
    global client, db, urls, url_stats

    MONGO_URI = os.getenv("MONGO_URI")

    print("🔎 MONGO_URI =", MONGO_URI)

    if not MONGO_URI:
        print("⚠️ MONGO_URI is not set. Running in NO-DB mode.")
        return False

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")

        db = client["tiny_url"]
        urls = db["urls"]
        url_stats = db["url_stats"]

        print("✅ MongoDB connected successfully")
        return True

    except ServerSelectionTimeoutError:
        print("⚠️ MongoDB not reachable. Running in NO-DB mode.")
        return False
    except Exception as e:
        print(f"⚠️ MongoDB error: {e}. Running in NO-DB mode.")
        return False


# Try once at import time
connect_db()
