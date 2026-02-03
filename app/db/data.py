import os
from typing import Any

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")
client: Any = MongoClient(MONGO_URI)

db = client["tiny_url"]
urls = db["urls"]
url_stats = db["url_stats"]
print("Mongo DB NAME:", urls.database.name)
print("Mongo COLLECTION:", urls.name)
