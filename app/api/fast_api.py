import datetime
from flask import request, jsonify
from app.utils.helper import generate_code, sanitize_url, is_valid_url
from app.utils import urls
from flask import Flask

app = Flask(__name__)


@app.route("/api/shorten", methods=["POST"])
def api_shorten_url():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"success": False, "error": "URL is required"}), 400

    original_url = sanitize_url(data["url"])

    if not is_valid_url(original_url):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid URL. Must start with http:// or https://",
                }
            ),
            400,
        )

    short_code = generate_code()
    while urls.find_one({"short_code": short_code}):
        short_code = generate_code()

    urls.insert_one(
        {
            "short_code": short_code,
            "original_url": original_url,
            "created_at": datetime.datetime.utcnow(),
            "visit_count": 0,
        }
    )

    short_url = request.host_url + short_code

    return (
        jsonify(
            {
                "success": True,
                "original_url": original_url,
                "short_url": short_url,
                "short_code": short_code,
            }
        ),
        201,
    )
