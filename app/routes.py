import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app import __version__
from app.utils import db
from app.utils.cache import (
    clear_cache,
    get_from_cache,
    get_recent_from_cache,
    get_short_from_cache,
    increment_visit_cache,
    list_cache_clean,
    remove_cache_key,
    rev_cache,
    set_cache_pair,
    url_cache,
)
from app.utils.config import (
    CACHE_PURGE_TOKEN,
    DOMAIN,
    MAX_RECENT_URLS,
    QR_DIR,
)
from app.utils.helper import (
    authorize_url,
    format_date,
    generate_code,
    is_valid_url,
    sanitize_url,
)
from app.utils.qr import generate_qr_with_logo

templates = Jinja2Templates(directory="app/templates")
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
    original_url = session.pop("original_url", None)
    short_code = session.pop("short_code", None)
    info_message = session.pop("info_message", None)
    error = session.pop("error", None)

    qr_image = None
    qr_data = None

    if qr_enabled and new_short_url and short_code:
        qr_data = new_short_url
        qr_filename = f"{short_code}.png"
        generate_qr_with_logo(qr_data, str(QR_DIR / qr_filename))
        qr_image = f"/qr/{qr_filename}"

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
    original_url = sanitize_url(original_url)  # sanitize the URL input

    if not original_url or not is_valid_url(original_url):  # validate the URL
        session["error"] = "Please enter a valid URL."
        session["original_url"] = original_url  # preserve user input
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    if not authorize_url(
        original_url
    ):  # authorize the URL based on whitelist/blacklist
        session["error"] = "This domain is not allowed."
        session["original_url"] = original_url  # preserve user input
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


@ui_router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@ui_router.get("/history", response_class=HTMLResponse)
async def recent_urls(request: Request):
    recent_urls_list = db.get_recent_urls(MAX_RECENT_URLS) or get_recent_from_cache(
        MAX_RECENT_URLS
    )

    return templates.TemplateResponse(
        "recent.html",
        {
            "request": request,
            "urls": recent_urls_list,
            "format_date": format_date,
            "db_available": db.get_collection() is not None,
            "get_visit_count_from_cache": increment_visit_cache,
        },
    )


@ui_router.get("/cache/list")
def cache_list_ui():
    return list_cache_clean()


@ui_router.delete("/cache/purge", response_class=PlainTextResponse)
def cache_purge_ui(x_cache_token: str = Header(..., alias="X-Cache-Token")):
    """
    Force delete everything from cache (secured by header)
    """
    if x_cache_token != CACHE_PURGE_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not url_cache and not rev_cache:
        return "No URLs in cache"

    clear_cache()
    return "cleared ALL"


@ui_router.patch("/cache/remove")
def cache_remove_one_ui(
    key: str = Query(..., description="short_code OR original_url"),
    x_cache_token: str = Header(..., alias="X-Cache-Token"),
):
    # 🔐 Header security
    if x_cache_token != CACHE_PURGE_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    removed = remove_cache_key(key)

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Key not found in cache.",
        )

    return {
        "status": "deleted",
    }


@ui_router.get("/{short_code}")
def redirect_short_ui(short_code: str, background_tasks: BackgroundTasks):
    cached_url = get_from_cache(short_code)
    if cached_url:
        if db.is_connected():
            background_tasks.add_task(db.increment_visit, short_code)
        else:
            increment_visit_cache(short_code)
        return RedirectResponse(cached_url)

    if db.is_connected():
        doc = db.increment_visit(short_code)
        if doc and doc.get("original_url"):
            set_cache_pair(short_code, doc["original_url"])
            return RedirectResponse(doc["original_url"])

    recent_cache = get_recent_from_cache(MAX_RECENT_URLS)
    for item in recent_cache or []:
        code = item.get("short_code") or item.get("code")
        if code == short_code:
            original_url = item.get("original_url")
            if original_url:
                set_cache_pair(short_code, original_url)
                return RedirectResponse(original_url)

    raise HTTPException(status_code=404, detail="Page not found")


@ui_router.delete("/history/{short_code}")
def delete_recent_api(short_code: str):
    recent = get_recent_from_cache(MAX_RECENT_URLS) or []
    removed_from_cache = False

    for i, item in enumerate(recent):
        code = item.get("short_code") or item.get("code")
        if code == short_code:
            recent.pop(i)  # remove from cache
            removed_from_cache = True
            break

    db_available = db.is_connected()
    db_deleted = False

    if db_available:
        db_deleted = db.delete_by_short_code(short_code)

    if not removed_from_cache and not db_deleted:
        raise HTTPException(
            status_code=404, detail=f"short_code '{short_code}' not found"
        )

    return {
        "success": True,
        "status": "deleted",
        "short_code": short_code,
        "db_deleted": db_deleted,
        "db_available": db_available,
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

    if not authorize_url(original_url):
        return JSONResponse(status_code=400, content={"error": "DOMAIN_NOT_ALLOWED"})

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


api_router.include_router(api_v1)
