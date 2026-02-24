from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.fast_api import app as api_app
from app.utils import db
from app.utils.cache import (
    get_from_cache,
    get_recent_from_cache,
    get_short_from_cache,
    rev_cache,
    set_cache_pair,
    url_cache,
)
from app.utils.config import DOMAIN, MAX_RECENT_URLS, SESSION_SECRET
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
    logger = logging.getLogger(__name__)
    logger.info("Application startup: Connecting to database...")
    db.connect_db()
    db.start_health_check()
    logger.info("Application startup complete")
    
    yield
    
    logger.info("Application shutdown: Cleaning up...")
    await db.stop_health_check()
    
    # Close MongoDB client gracefully
    try:
        if db.client is not None:
            db.client.close()
            logger.info("MongoDB client closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB client: {str(e)}")
    
    logger.info("Application shutdown complete")


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

    all_urls = db.get_recent_urls(MAX_RECENT_URLS) or get_recent_from_cache(
        MAX_RECENT_URLS
    )

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
            "db_available": db.get_collection() is not None,
        },
    )


@app.post("/shorten", response_class=RedirectResponse)
async def create_short_url(
    request: Request,
    original_url: str = Form(""),
    generate_qr: Optional[str] = Form(None),
    qr_type: str = Form("short"),
) -> RedirectResponse:
    logger = logging.getLogger(__name__)
    
    session = request.session
    qr_enabled = bool(generate_qr)
    original_url = sanitize_url(original_url)

    # Basic validation (FastAPI can also handle this via Pydantic)
    if not original_url or not is_valid_url(original_url):
        session["error"] = "Please enter a valid URL."
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    # 1. Try Cache First
    short_code: Optional[str] = get_short_from_cache(original_url)

    if not short_code:
        # 2. Try Database if connected
        if db.is_connected():
            existing = db.find_by_original_url(original_url)
            db_code = existing.get("short_code") if existing else None
            if isinstance(db_code, str):
                short_code = db_code
                set_cache_pair(short_code, original_url)

        # 3. Generate New if still None
        if not short_code:
            short_code = generate_code()
            set_cache_pair(short_code, original_url)
            
            # Only write to database if connected
            if db.is_connected():
                db.insert_url(short_code, original_url)
            else:
                logger.warning(f"Database not connected, URL {short_code} created in cache only")
                session["info_message"] = "URL created (database temporarily unavailable)"

    # --- TYPE GUARD FOR MYPY ---
    if not isinstance(short_code, str):
        session["error"] = "Internal server error: Code generation failed."
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    # Mypy now knows short_code is strictly 'str'
    new_short_url = build_short_url(short_code, DOMAIN)

    session.update(
        {
            "new_short_url": new_short_url,
            "qr_enabled": qr_enabled,
            "qr_type": qr_type,
            "original_url": original_url,
            "short_code": short_code,
        }
    )

    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/recent", response_class=HTMLResponse)
async def recent_urls(request: Request):
    recent_urls_list = db.get_recent_urls(
        MAX_RECENT_URLS
    ) or get_recent_from_cache(MAX_RECENT_URLS)

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
    db.delete_by_short_code(short_code)

    cached = url_cache.pop(short_code, None)
    if cached:
        rev_cache.pop(cached.get("url"), None)

    return PlainTextResponse("", status_code=204)


#@app.get("/{short_code}")
#async def redirect_short(request: Request, short_code: str):
#    logger = logging.getLogger(__name__)
#    # Try cache first
#    cached_url = get_from_cache(short_code)
#    if cached_url:
#        return RedirectResponse(cached_url)

#    # Check if database is connected
#    if not db.is_connected():
#        logger.warning(f"Database not connected, cannot redirect {short_code}")
#        return PlainTextResponse(
#            "Service temporarily unavailable. Please try again later.",
#            status_code=503,
#            headers={"Retry-After": "30"},
#        )

#    # Try database
#    doc = db.increment_visit(short_code)
#    if doc:
#        set_cache_pair(short_code, doc["original_url"])
#        return RedirectResponse(doc["original_url"])

#    return PlainTextResponse("Invalid or expired short URL", status_code=404)

@app.get("/{short_code}")
async def redirect_short(request: Request, short_code: str):
    logger = logging.getLogger(__name__)
    # Try cache first
    cached_url = get_from_cache(short_code)
    if cached_url:

        if db.is_connected():
            db.increment_visit(short_code)
        else:
            from app.utils.cache import increment_cache_visit
            increment_cache_visit(short_code)

        return RedirectResponse(cached_url)
    
    # Check if database is connected
    if not db.is_connected():
        logger.warning(f"Database not connected, cannot redirect {short_code}")
        return PlainTextResponse(
            "Service temporarily unavailable. Please try again later.",
            status_code=503,
            headers={"Retry-After": "30"}
        )
    
    # Try database
    doc = db.increment_visit(short_code)
    if doc:
        set_cache_pair(short_code, doc["original_url"])
        return RedirectResponse(doc["original_url"])
    
    return PlainTextResponse("Invalid or expired short URL", status_code=404)


@app.get("/coming-soon", response_class=HTMLResponse)
async def coming_soon(request: Request):
    return templates.TemplateResponse("coming-soon.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint showing database and cache status."""
    state = db.get_connection_state()
    
    response_data = {
        "database": state,
        "cache": {
            "enabled": True,
            "size": len(url_cache),
        }
    }
    
    status_code = 200 if state["connected"] else 503
    return JSONResponse(content=response_data, status_code=status_code)


app.mount("/api", api_app)


@app.get("/_debug/cache")
async def debug_cache():
    return {
        "url_cache": url_cache,
        "rev_cache": rev_cache,
        "recent_from_cache": get_recent_from_cache(MAX_RECENT_URLS),
        "size": {
            "url_cache": len(url_cache),
            "rev_cache": len(rev_cache),
        },
    }
