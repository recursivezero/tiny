import datetime
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo.errors import PyMongoError
from starlette.middleware.sessions import SessionMiddleware


from app.api.fast_api import app as api_app
from app.db.data import urls
from app.qr import generate_qr_with_logo
from app.utils.config import load_env
from app.utils.helper import (
    format_date,
    generate_code,
    is_valid_url,
    sanitize_url,
)

# Decide which env file to load (kept exactly as you had)
env = os.getenv("ENV", "development")

file_map = {
    "production": ".env",
    "local": ".env.local",
    "development": ".env.development",
}

load_env()  # explicit call

app = FastAPI(title="TinyURL")

# Equivalent of Flask secret_key (session support)
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# Static + templates
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
QR_DIR = STATIC_DIR / "qr"
QR_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def db_available():
    return urls is not None


def build_short_url(short_code: str, request_host_url: str) -> str:
    base_url = os.getenv("DOMAIN", request_host_url).rstrip("/")
    return f"{base_url}/{short_code}"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    session = request.session

    new_short_url = session.pop("new_short_url", None)
    qr_enabled = session.pop("qr_enabled", False)
    qr_type = session.pop("qr_type", "short")
    original_url = session.pop("original_url", None)
    short_code = session.pop("short_code", None)
    info_message = session.pop("info_message", None)
    error = session.pop("error", None)

    qr_image = None
    qr_data = None

    if qr_enabled and new_short_url and short_code:
        qr_data = new_short_url if qr_type == "short" else original_url
        qr_filename = f"{short_code}.png"

        QR_DIR.mkdir(parents=True, exist_ok=True)
        generate_qr_with_logo(qr_data, qr_filename)
        qr_image = f"/static/qr/{qr_filename}"

    all_urls = []
    try:
        if db_available():
            all_urls = list(urls.find().sort("created_at", -1))
    except PyMongoError:
        all_urls = []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "urls": all_urls,
            "new_short_url": new_short_url,
            "error": error,
            "info_message": info_message,
            "qr_data": qr_data,
            "qr_enabled": qr_enabled,
            "qr_type": qr_type,
            "qr_image": qr_image,
        },
    )


@app.post("/", response_class=RedirectResponse)
async def create_short_url(
    request: Request,
    original_url: str = Form(""),
    generate_qr: Optional[str] = Form(None),
    qr_type: str = Form("short"),
):
    session = request.session

    qr_enabled = generate_qr == "on"
    original_url = sanitize_url(original_url)

    if not original_url:
        session["error"] = "URL cannot be empty."
        return RedirectResponse("/", status_code=303)

    if not is_valid_url(original_url):
        session["error"] = (
            "Please enter a valid URL (must start with http:// or https://)."
        )
        return RedirectResponse("/", status_code=303)

    if not db_available():
        short_code = generate_code()
        new_short_url = build_short_url(short_code, str(request.base_url))
        session.update(
            {
                "new_short_url": new_short_url,
                "qr_enabled": qr_enabled,
                "qr_type": qr_type,
                "original_url": original_url,
                "short_code": short_code,
            }
        )
        return RedirectResponse("/", status_code=303)

    try:
        existing = urls.find_one(
            {"original_url": original_url},
            sort=[("created_at", 1)],
        )
    except PyMongoError:
        short_code = generate_code()
        new_short_url = build_short_url(short_code, str(request.base_url))
        session.update(
            {
                "new_short_url": new_short_url,
                "qr_enabled": qr_enabled,
                "qr_type": qr_type,
                "original_url": original_url,
                "short_code": short_code,
            }
        )
        return RedirectResponse("/", status_code=303)

    if existing:
        short_code = existing["short_code"]
        session["info_message"] = "Already shortened before — using existing short URL."
    else:
        short_code = generate_code()
        while True:
            try:
                if not urls.find_one({"short_code": short_code}):
                    break
                short_code = generate_code()
            except PyMongoError:
                break

        try:
            urls.insert_one(
                {
                    "short_code": short_code,
                    "original_url": original_url,
                    "created_at": datetime.datetime.utcnow(),
                    "visit_count": 0,
                    "meta": {},
                }
            )
        except PyMongoError:
            session

    new_short_url = build_short_url(short_code, str(request.base_url))

    session.update(
        {
            "new_short_url": new_short_url,
            "qr_enabled": qr_enabled,
            "qr_type": qr_type,
            "original_url": original_url,
            "short_code": short_code,
        }
    )

    return RedirectResponse("/", status_code=303)


@app.get("/recent", response_class=HTMLResponse)
async def recent_urls(request: Request):
    recent_urls_list = []
    try:
        if db_available():
            recent_urls_list = list(urls.find().sort("created_at", -1))
    except PyMongoError:
        recent_urls_list = []

    return templates.TemplateResponse(
        "recent.html",
        {
            "request": request,
            "urls": recent_urls_list,
            "format_date": format_date,
        },
    )


@app.get("/coming-soon", response_class=HTMLResponse)
async def coming_soon(request: Request):
    return templates.TemplateResponse("coming-soon.html", {"request": request})


@app.post("/delete/{short_code}")
async def delete_url(short_code: str):
    if not db_available():
        return PlainTextResponse("Database is not connected.", status_code=503)

    try:
        urls.delete_one({"short_code": short_code})
    except PyMongoError:
        return PlainTextResponse("Database connection lost.", status_code=503)

    return PlainTextResponse("", status_code=204)


@app.get("/{short_code}")
async def redirect_short(short_code: str):
    if not db_available():
        return PlainTextResponse(
            "Database is not connected. Redirection is unavailable right now.",
            status_code=503,
        )

    try:
        doc = urls.find_one_and_update(
            {"short_code": short_code},
            {"$inc": {"visit_count": 1}},
        )
    except PyMongoError:
        return PlainTextResponse(
            "Database connection lost. Try again later.", status_code=503
        )

    if doc:
        return RedirectResponse(doc["original_url"])

    return PlainTextResponse("Invalid or expired short URL", status_code=404)


app.mount("/api", api_app)
