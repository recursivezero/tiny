import datetime
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.fast_api import app as api_app
from app.db import data as db_data
from app.utils.config import load_env
from app.utils.helper import (
    format_date,
    generate_code,
    is_valid_url,
    sanitize_url,
)
from app.utils.qr import generate_qr_with_logo

load_env()  # ✅ load env ONCE

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
RESET = "\033[0m"

app_name = os.getenv("APP_NAME", "TinyURL")
print(f"Environment loaded as {BLUE}{app_name}{RESET}")

# 1. MongoDB error handling: Try to import the real exception class first
PyMongoError: Any
try:
    from pymongo.errors import PyMongoError as _RealPyMongoError

    PyMongoError = _RealPyMongoError
except (ImportError, ModuleNotFoundError):
    # 2. Fallback: Define our own only if the real one fails
    class _FallbackPyMongoError(Exception):
        pass

    # Assign our fallback to the same local name
    PyMongoError = _FallbackPyMongoError


# -----------------------------
# Lifespan: env + DB connect ONCE
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    connected = db_data.connect_db()  # ✅ connect DB ONCE
    app.state.db_available = connected
    yield


app = FastAPI(title="TinyURL", lifespan=lifespan)


app.add_middleware(SessionMiddleware, secret_key="super-secret-key")


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def db_available(request: Request) -> bool:
    return getattr(request.app.state, "db_available", False)


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
        generate_qr_with_logo(qr_data, qr_filename)
        qr_image = f"/static/qr/{qr_filename}"

    all_urls = []
    if db_available(request) and db_data.urls is not None:
        try:
            all_urls = list(db_data.urls.find().sort("created_at", -1))
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
            "db_available": db_available(request),
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

    short_code = None

    if db_available(request) and db_data.urls is not None:
        try:
            existing = db_data.urls.find_one({"original_url": original_url})
            if existing:
                short_code = existing["short_code"]
                session["info_message"] = (
                    "Already shortened before — using existing short URL."
                )
        except PyMongoError:
            pass

    if not short_code:
        short_code = generate_code()

    if db_available(request) and db_data.urls is not None:
        try:
            db_data.urls.insert_one(
                {
                    "short_code": short_code,
                    "original_url": original_url,
                    "created_at": datetime.datetime.utcnow(),
                    "visit_count": 0,
                }
            )
        except PyMongoError:
            pass

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
    if db_available(request) and db_data.urls is not None:
        try:
            recent_urls_list = list(db_data.urls.find().sort("created_at", -1))
        except PyMongoError:
            pass

    return templates.TemplateResponse(
        "recent.html",
        {"request": request, "urls": recent_urls_list, "format_date": format_date},
    )


@app.post("/delete/{short_code}")
async def delete_url(request: Request, short_code: str):
    if db_available(request) and db_data.urls is not None:
        try:
            db_data.urls.delete_one({"short_code": short_code})
        except PyMongoError:
            return PlainTextResponse("Database connection lost.", status_code=503)

    return RedirectResponse("/recent", status_code=303)


@app.get("/{short_code}")
async def redirect_short(request: Request, short_code: str):
    if not db_available(request) or db_data.urls is None:
        return PlainTextResponse("Database is not connected.", status_code=503)

    try:
        doc = db_data.urls.find_one_and_update(
            {"short_code": short_code},
            {"$inc": {"visit_count": 1}},
        )
    except PyMongoError:
        return PlainTextResponse("Database connection lost.", status_code=503)

    if not doc:
        return PlainTextResponse("Invalid or expired short URL", status_code=404)

    return RedirectResponse(doc["original_url"])


app.mount("/api", api_app)
