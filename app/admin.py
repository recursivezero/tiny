import datetime
import json
from db.data import urls
from routs import admin
from flask import render_template, request, send_file


@admin.route("/admin", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        if "json_file" not in request.files:
            return "No file uploaded!", 400

        json_file = request.files["json_file"]

        if json_file.filename == "":
            return "Please select a JSON file", 400

        if not json_file.filename.lower().endswith(".json"):
            return "Invalid file type! Only .json allowed", 400

        try:
            data = json.load(json_file)
        except Exception:
            return "Invalid JSON format!", 400

        if not isinstance(data, list):
            return "JSON must contain a list of objects", 400

        required_fields = [
            "short_code",
            "original_url",
            "created_at",
            "visit_count",
            "meta",
        ]

        for index, item in enumerate(data):
            if not isinstance(item, dict):
                return f"Item {index} must be an object", 400
            for f in required_fields:
                if f not in item:
                    return f"Missing field '{f}' at index {index}", 400
            if not item["original_url"].startswith(("http://", "https://")):
                return f"Invalid URL at index {index}", 400

            try:
                datetime.datetime.fromisoformat(item["created_at"])
            except Exception:
                return f"Invalid created_at timestamp at index {index}", 400

            if not isinstance(item["visit_count"], int):
                return f"visit_count must be integer at index {index}", 400

            if not isinstance(item["meta"], dict):
                return f"meta must be dictionary at index {index}", 400
        for item in data:
            created_at = datetime.datetime.fromisoformat(item["created_at"])
            existing = urls.find_one({"short_code": item["short_code"]})
            if existing:
                urls.update_one(
                    {"short_code": item["short_code"]},
                    {
                        "$set": {
                            "visit_count": max(
                                existing["visit_count"], item["visit_count"]
                            )
                        }
                    },
                )
            else:
                urls.insert_one(
                    {
                        "short_code": item["short_code"],
                        "original_url": item["original_url"],
                        "created_at": created_at,
                        "visit_count": item["visit_count"],
                        "meta": item["meta"],
                    }
                )

    all_urls = list(urls.find().sort("created_at", -1))
    return render_template("admin.html", urls=all_urls)


@admin.route("/export")
def export_json():
    export = []
    for u in urls.find():
        export.append(
            {
                "short_code": u["short_code"],
                "original_url": u["original_url"],
                "created_at": u["created_at"].isoformat(),
                "visit_count": u["visit_count"],
                "meta": u["meta"],
            }
        )

    path = "urls_export.json"
    with open(path, "w") as f:
        json.dump(export, f, indent=4)

    return send_file(path, as_attachment=True)
