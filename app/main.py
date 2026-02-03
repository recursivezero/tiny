import datetime

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

from app.db.data import urls
from app.qr import generate_qr_with_logo
from app.utils.helper import (
    format_date,
    generate_code,
    is_valid_url,
    sanitize_url,
)

load_dotenv(dotenv_path="/mnt/d/projects/tiny/.env.local")


app = Flask(__name__)
app.secret_key = "super-secret-key"


@app.route("/", methods=["GET", "POST"])
def index():
    new_short_url = None
    error = None
    info_message = None
    qr_data = None
    qr_enabled = False
    qr_type = "short"
    qr_image = None
    qr_filename = None

    if request.method == "POST":
        original_url = request.form.get("original_url", "")
        qr_enabled = request.form.get("generate_qr") == "on"
        qr_type = request.form.get("qr_type", "short") if qr_enabled else "short"

        original_url = sanitize_url(original_url)

        if not original_url:
            error = "URL cannot be empty."
        elif not is_valid_url(original_url):
            error = "Please enter a valid URL (must start with http:// or https://)."
        else:
            existing = urls.find_one(
                {"original_url": original_url},
                sort=[("created_at", 1)],
            )

            if existing:
                short_code = existing["short_code"]
                session["info_message"] = (
                    "Already shortened before — using existing short URL."
                )
            else:
                session.pop("info_message", None)

                short_code = generate_code()
                while urls.find_one({"short_code": short_code}):
                    short_code = generate_code()

                urls.insert_one(
                    {
                        "short_code": short_code,
                        "original_url": original_url,
                        "created_at": datetime.datetime.utcnow(),
                        "visit_count": 0,
                        "meta": {},
                    }
                )

            new_short_url = request.host_url + short_code

            session["new_short_url"] = new_short_url
            session["qr_enabled"] = qr_enabled
            session["qr_type"] = qr_type
            session["original_url"] = original_url
            session["short_code"] = short_code

            return redirect(url_for("index"))

    new_short_url = session.pop("new_short_url", None)
    qr_enabled = session.pop("qr_enabled", False)
    qr_type = session.pop("qr_type", "short")
    original_url = session.pop("original_url", None)
    short_code = session.pop("short_code", None)
    info_message = session.pop("info_message", None)

    if qr_enabled and new_short_url and short_code:
        qr_data = new_short_url if qr_type == "short" else original_url
        qr_filename = f"{short_code}.png"
        generate_qr_with_logo(qr_data, qr_filename)
        qr_image = f"/static/qr/{qr_filename}"

    all_urls = list(urls.find().sort("created_at", -1))

    return render_template(
        "index.html",
        urls=all_urls,
        new_short_url=new_short_url,
        error=error,
        info_message=info_message,
        qr_data=qr_data,
        qr_enabled=qr_enabled,
        qr_type=qr_type,
        all_urls=all_urls,
        qr_image=qr_image,
    )


@app.route("/<short_code>")
def redirect_short(short_code):
    doc = urls.find_one_and_update(
        {"short_code": short_code},
        {"$inc": {"visit_count": 1}},
    )
    if doc:
        return redirect(doc["original_url"])
    return "Invalid or expired short URL", 404


@app.route("/delete/<short_code>", methods=["POST"])
def delete_url(short_code):
    urls.delete_one({"short_code": short_code})
    return "", 204


@app.route("/coming-soon")
def coming_soon():
    return render_template("coming-soon.html")


@app.route("/recent")
def recent_urls():
    recent_urls_list = list(urls.find().sort("created_at", -1))
    return render_template(
        "recent.html",
        urls=recent_urls_list,
        format_date=format_date,
    )
