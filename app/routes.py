import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    JSONResponse,
)
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app import __version__
from app.utils import db
from app.utils.cache import (
    get_from_cache,
    get_recent_from_cache,
    get_short_from_cache,
    set_cache_pair,
    url_cache,
    rev_cache,
)
from app.utils.config import DOMAIN, MAX_RECENT_URLS, MODE
from app.utils.helper import generate_code, is_valid_url, sanitize_url, format_date
from app.utils.qr import generate_qr_with_logo

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Routers
ui_router = APIRouter()
api_router = APIRouter()
api_v1 = APIRouter(prefix=os.getenv("API_VERSION", "/api/v1"), tags=["v1"])


# ---------------- UI ROUTES ----------------


@ui_router.get("/", response_class=HTMLResponse)
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
        qr_dir = BASE_DIR / "static" / "qr"
        qr_dir.mkdir(parents=True, exist_ok=True)
        generate_qr_with_logo(qr_data, str(qr_dir / qr_filename))
        qr_image = f"/static/qr/{qr_filename}"

    recent_urls = db.get_recent_urls(MAX_RECENT_URLS) or get_recent_from_cache(
        MAX_RECENT_URLS
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "urls": recent_urls,
            "new_short_url": new_short_url,
            "qr_image": qr_image,
            "qr_data": qr_data,
            "qr_enabled": qr_enabled,
            "original_url": original_url,
            "error": error,
            "info_message": info_message,
            "db_available": db.get_collection() is not None,
        },
    )


@ui_router.post("/shorten", response_class=RedirectResponse)
async def create_short_url(
    request: Request,
    original_url: str = Form(""),
    generate_qr: Optional[str] = Form(None),
    qr_type: str = Form("short"),
):
    session = request.session
    original_url = sanitize_url(original_url)

    if not original_url or not is_valid_url(original_url):
        session["error"] = "Please enter a valid URL."
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    short_code: Optional[str] = get_short_from_cache(original_url)

    if not short_code and db.is_connected():
        existing = db.find_by_original_url(original_url)
        db_code = (existing.get("short_code") if existing else None) or (
            existing.get("code") if existing else None
        )
        if isinstance(db_code, str):
            short_code = db_code
            set_cache_pair(short_code, original_url)

    if not short_code:
        short_code = generate_code()
        set_cache_pair(short_code, original_url)
        if db.is_connected():
            db.insert_url(short_code, original_url)

    session.update(
        {
            "new_short_url": f"{DOMAIN.rstrip('/')}/{short_code}",
            "short_code": short_code,
            "qr_enabled": bool(generate_qr),
            "qr_type": qr_type,
            "original_url": original_url,
        }
    )

    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@ui_router.get("/recent", response_class=HTMLResponse)
async def recent_urls(request: Request):
    recent_urls_list = db.get_recent_urls(MAX_RECENT_URLS) or get_recent_from_cache(
        MAX_RECENT_URLS
    )

    return templates.TemplateResponse(
        "recent.html",
        {"request": request, "urls": recent_urls_list, "format_date": format_date},
    )


@ui_router.get("/{short_code}")
def redirect_short_ui(short_code: str):
    cached_url = get_from_cache(short_code)
    if cached_url:
        return RedirectResponse(cached_url)

    if db.is_connected():
        doc = db.increment_visit(short_code)
        if doc and doc.get("original_url"):
            set_cache_pair(short_code, doc["original_url"])
            return RedirectResponse(doc["original_url"])

        recent_db = db.get_recent_urls(MAX_RECENT_URLS)
        for item in recent_db or []:
            code = item.get("short_code") or item.get("code")
            if code == short_code:
                original_url = item.get("original_url")
                if original_url:
                    set_cache_pair(short_code, original_url)
                    return RedirectResponse(original_url)

    recent_cache = get_recent_from_cache(MAX_RECENT_URLS)
    for item in recent_cache or []:
        code = item.get("short_code") or item.get("code")
        if code == short_code:
            original_url = item.get("original_url")
            if original_url:
                set_cache_pair(short_code, original_url)
                return RedirectResponse(original_url)

    return PlainTextResponse("Invalid short URL", status_code=404)


@ui_router.get("/debug/cache", include_in_schema=False)
def ui_debug_cache():
    if MODE != "local":
        return PlainTextResponse("Not Found", status_code=404)

    return {
        "url_cache": url_cache,
        "rev_cache": rev_cache,
        "recent_from_cache": get_recent_from_cache(MAX_RECENT_URLS),
        "size": {
            "url_cache": len(url_cache),
            "rev_cache": len(rev_cache),
        },
    }


# ---------------- API ROUTES ----------------


@api_router.get("/", response_class=HTMLResponse, tags=["Home"])
async def read_root(_: Request):
    return """
    <html>
        <head>
            <title>🌙 tiny API 🌙</title>
            <style>
                body {
                    margin: 0;
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(180deg, #0b1220, #050b14);
                    font-family: "Poppins", system-ui, Arial, sans-serif;
                    color: #f8fafc;
                }
                .card {
                    background: rgba(255, 255, 255, 0.06);
                    backdrop-filter: blur(12px);
                    border-radius: 16px;
                    padding: 50px 40px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                    max-width: 520px;
                    width: 90%;
                }
                h1 {
                    font-size: 2.8em;
                    margin-bottom: 12px;
                    background: linear-gradient(90deg, #5ab9ff, #4cb39f);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                p {
                    font-size: 1.1em;
                    color: #cbd5e1;
                    margin-bottom: 30px;
                }
                a {
                    display: inline-block;
                    padding: 14px 26px;
                    border-radius: 12px;
                    background: linear-gradient(90deg, #4cb39f, #5ab9ff);
                    color: #fff;
                    text-decoration: none;
                    font-weight: 700;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🚀 tiny API</h1>
                <p>FastAPI backend for the Tiny URL shortener</p>
                <a href="/docs">View API Documentation</a>
            </div>
        </body>
    </html>
    """


@api_router.get("/version")
def api_version():
    return {"version": __version__}


class ShortenRequest(BaseModel):
    url: str = Field(..., examples=["https://abcdkbd.com"])


@api_v1.post("/shorten")
def shorten_api(payload: ShortenRequest):
    original_url = sanitize_url(payload.url)
    if not is_valid_url(original_url):
        return JSONResponse(status_code=400, content={"error": "INVALID_URL"})

    short_code = get_short_from_cache(original_url)
    if not short_code:
        short_code = generate_code()
        set_cache_pair(short_code, original_url)
        if db.is_connected():
            db.insert_url(short_code, original_url)

    return {
        "success": True,
        "input_url": original_url,
        "short_code": short_code,
        "created_on": datetime.now(timezone.utc),
    }


@api_router.get("/health")
def health():
    return {
        "db": db.get_connection_state(),
        "cache_size": len(url_cache),
    }


@api_router.get("/_debug/cache", include_in_schema=False)
def debug_cache():
    return {
        "url_cache": url_cache,
        "rev_cache": rev_cache,
        "recent_from_cache": get_recent_from_cache(MAX_RECENT_URLS),
        "size": {
            "url_cache": len(url_cache),
            "rev_cache": len(rev_cache),
        },
    }


@api_router.get("/{short_code}")
def redirect_short_api(short_code: str):
    cached_url = get_from_cache(short_code)
    if cached_url:
        return RedirectResponse(cached_url)

    if db.is_connected():
        doc = db.increment_visit(short_code)
        if doc and doc.get("original_url"):
            set_cache_pair(short_code, doc["original_url"])
            return RedirectResponse(doc["original_url"])

    recent = get_recent_from_cache(MAX_RECENT_URLS)
    for item in recent or []:
        code = item.get("short_code") or item.get("code")
        if code == short_code:
            original_url = item.get("original_url")
            if original_url:
                set_cache_pair(short_code, original_url)
                return RedirectResponse(original_url)

    return PlainTextResponse("Invalid short URL", status_code=404)


api_router.include_router(api_v1)
