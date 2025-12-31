import os
from typing import Any

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")
client: Any = MongoClient(MONGO_URI)

db = client["url_shortener"]
urls = db["urls"]
