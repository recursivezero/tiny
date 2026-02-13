import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

if TYPE_CHECKING:
    from pymongo.errors import PyMongoError
else:
    try:
        from pymongo.errors import PyMongoError
    except ImportError:

        class PyMongoError(Exception):
            pass


from app.api.fast_api import app as api_app
from app.utils import data as db_data
from app.utils.cache import (
    get_from_cache,
    get_short_from_cache,
    rev_cache,
    set_cache_pair,
    url_cache,
    add_recent,
    get_recent,
)
from app.utils.config import load_env, SESSION_SECRET, DOMAIN
from app.utils.helper import (
    format_date,
    generate_code,
    is_valid_url,
    sanitize_url,
)
from app.utils.qr import generate_qr_with_logo


# -----------------------------
# Lifespan: env + DB connect ONCE
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_env()
    db_data.connect_db()
    yield


app = FastAPI(title="TinyURL", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def build_short_url(short_code: str, request_host_url: str) -> str:
    base_url = DOMAIN.rstrip("/")
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
        qr_dir = STATIC_DIR / "qr"
        qr_dir.mkdir(parents=True, exist_ok=True)
        generate_qr_with_logo(qr_data, str(qr_dir / qr_filename))
        qr_image = f"/static/qr/{qr_filename}"

    collection = db_data.get_collection()

    if collection is not None:
        try:
            all_urls = list(collection.find().sort("created_at", -1).limit(10))
        except PyMongoError:
            all_urls = get_recent()
    else:
        all_urls = get_recent()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "urls": all_urls,
            "new_short_url": new_short_url,
            "qr_image": qr_image,
            "qr_data": qr_data,
            "qr_enabled": qr_enabled,
            "original_url": original_url,
            "error": error,
            "info_message": info_message,
            "db_available": collection is not None,
        },
    )


@app.post("/shorten", response_class=RedirectResponse)
async def create_short_url(
    request: Request,
    original_url: str = Form(""),
    generate_qr: Optional[str] = Form(None),
    qr_type: str = Form("short"),
):
    session = request.session
    qr_enabled = generate_qr == "true"
    original_url = sanitize_url(original_url)

    if not original_url:
        session["error"] = "URL cannot be empty."
        return RedirectResponse("/", status_code=303)

    if not is_valid_url(original_url):
        session["error"] = (
            "Please enter a valid URL (must start with http:// or https://)."
        )
        return RedirectResponse("/", status_code=303)

    cached_short = get_short_from_cache(original_url)
    if cached_short:
        short_code = cached_short
        session["info_message"] = "Already shortened before — fetched from cache."
        add_recent(short_code, original_url)
    else:
        short_code = None

        collection = db_data.get_collection()

        if collection is not None:
            try:
                existing = collection.find_one({"original_url": original_url})
                if existing:
                    short_code = existing["short_code"]
                    set_cache_pair(short_code, original_url)
                    session["info_message"] = (
                        "Already shortened before — fetched from database."
                    )
                    add_recent(short_code, original_url)
            except PyMongoError:
                pass

        if not short_code:
            short_code = generate_code()
            set_cache_pair(short_code, original_url)

            if collection is not None:
                try:
                    collection.insert_one(
                        {
                            "short_code": short_code,
                            "original_url": original_url,
                            "created_at": datetime.datetime.utcnow(),
                            "visit_count": 0,
                        }
                    )
                except PyMongoError:
                    pass

            add_recent(short_code, original_url)

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
    collection = db_data.get_collection()

    if collection is not None:
        try:
            recent_urls_list = list(collection.find().sort("created_at", -1).limit(10))
        except PyMongoError:
            recent_urls_list = get_recent()
    else:
        recent_urls_list = get_recent()

    normalized = []
    for item in recent_urls_list:
        normalized.append(
            {
                "short_code": item.get("short_code"),
                "original_url": item.get("original_url"),
                "created_at": item.get("created_at"),
                "visit_count": item.get("visit_count", 0),
            }
        )

    return templates.TemplateResponse(
        "recent.html",
        {
            "request": request,
            "urls": normalized,
            "format_date": format_date,
        },
    )


@app.post("/delete/{short_code}")
async def delete_url(request: Request, short_code: str):
    collection = db_data.get_collection()

    if collection is not None:
        try:
            collection.delete_one({"short_code": short_code})
        except PyMongoError:
            return PlainTextResponse("Database connection lost.", status_code=503)

    cached = url_cache.pop(short_code, None)
    if cached:
        rev_cache.pop(cached.get("url"), None)

    try:
        from app.utils.cache import recent_urls

        recent_urls[:] = [
            item for item in recent_urls if item.get("short_code") != short_code
        ]
    except Exception:
        pass

    return PlainTextResponse("", status_code=204)


@app.get("/{short_code}")
async def redirect_short(request: Request, short_code: str):
    collection = db_data.get_collection()

    # Always try to increment visit count if DB is available
    if collection is not None:
        try:
            doc = collection.find_one_and_update(
                {"short_code": short_code},
                {"$inc": {"visit_count": 1}},
            )
        except PyMongoError:
            doc = None
    else:
        doc = None

    # Then resolve URL (cache first, DB fallback)
    cached_url = get_from_cache(short_code)
    if cached_url:
        add_recent(short_code, cached_url)
        return RedirectResponse(cached_url)

    if doc:
        set_cache_pair(short_code, doc["original_url"])
        add_recent(short_code, doc["original_url"])
        return RedirectResponse(doc["original_url"])

    if collection is None:
        return PlainTextResponse("Database is not connected.", status_code=503)

    return PlainTextResponse("Invalid or expired short URL", status_code=404)


@app.get("/coming-soon", response_class=HTMLResponse)
async def coming_soon(request: Request):
    return templates.TemplateResponse("coming-soon.html", {"request": request})


app.mount("/api", api_app)


@app.get("/_debug/cache")
async def debug_cache():
    return {
        "url_cache": url_cache,
        "rev_cache": rev_cache,
        "recent": get_recent(),
        "size": {
            "url_cache": len(url_cache),
            "rev_cache": len(rev_cache),
        },
    }
