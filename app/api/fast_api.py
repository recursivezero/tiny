import os
import re
import traceback
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from app import __version__
from app.db import data as db_data
from app.utils.helper import generate_code, is_valid_url, sanitize_url

SHORT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{6}$")

# Load env
load_dotenv()

DOMAIN = os.getenv("DOMAIN", "http://127.0.0.1")
PORT = os.getenv("PORT", "8000")

print(f"Starting Tiny API on {DOMAIN}:{PORT}")

MAX_URL_LENGTH = 2048

# -------------------------------------------------
# App
# -------------------------------------------------
app = FastAPI(
    title="Tiny API",
    version=__version__,
    description="Tiny URL Shortener API built with FastAPI",
)


# -------------------------------------------------
# Global error handler
# -------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Something went wrong on the server",
        },
    )


# -------------------------------------------------
# Router
# -------------------------------------------------
api_v1 = APIRouter(prefix=os.getenv("API_VERSION", "/api/v1"), tags=["v1"])


# -------------------------------------------------
# Models
# -------------------------------------------------
class ShortenRequest(BaseModel):
    url: str = Field(..., examples=["https://abcdkbd.com"])


class ShortenResponse(BaseModel):
    success: bool = True
    input_url: str
    short_code: str
    created_on: datetime


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    input_url: str
    message: str


class VersionResponse(BaseModel):
    version: str


# -------------------------------------------------
# Home
# -------------------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["Home"])
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


@api_v1.post(
    "/shorten",
    response_model=ShortenResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
    status_code=201,
)
def shorten_url(payload: ShortenRequest):
    print(" SHORTEN ENDPOINT HIT ", payload.url)
    raw_url = payload.url.strip()

    if len(raw_url) > MAX_URL_LENGTH:
        return JSONResponse(
            status_code=413,
            content={
                "success": False,
                "input_url": payload.url,
                "message": "URL length exceeds maximum limit",
            },
        )

    # 2️⃣ Protocol presence check (http / https only)
    if not raw_url.startswith(("http", "https")):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "INVALID_PROTOCOL",
                "input_url": payload.url,
                "message": "URL must start with http:// or https://",
            },
        )

    # 3️⃣ Sanitize AFTER protocol presence
    original_url = sanitize_url(raw_url)

    if not is_valid_url(original_url):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "INVALID_URL",
                "input_url": payload.url,
                "message": "URL format is invalid",
            },
        )

    # 🔁 Try reconnect if DB dropped
    try:
        if db_data.urls is None or db_data.url_stats is None:
            db_data.connect_db()
    except Exception:
        pass

    # 🔌 Offline fallback if DB still unavailable
    if db_data.urls is None or db_data.url_stats is None:
        short_code = generate_code()
        created_at = datetime.now(timezone.utc)
        print("⚠️ DB disconnected at runtime. API offline mode.")
        return {
            "success": True,
            "input_url": original_url,
            "short_code": short_code,
            "created_on": created_at,
        }

    try:
        existing = db_data.urls.find_one(
            {"original_url": original_url}, sort=[("created_at", 1)]
        )
    except PyMongoError:
        short_code = generate_code()
        created_at = datetime.now(timezone.utc)
        print("⚠️ DB error during request. API offline mode.")
        return {
            "success": True,
            "input_url": original_url,
            "short_code": short_code,
            "created_on": created_at,
        }

    if existing:
        return {
            "success": True,
            "input_url": original_url,
            "short_code": existing["short_code"],
            "created_on": existing["created_at"],
        }

    # 6️⃣ Create new short code
    short_code = generate_code()
    while True:
        try:
            if not db_data.urls.find_one({"short_code": short_code}):
                break
            short_code = generate_code()
        except PyMongoError:
            break

    created_at = datetime.now(timezone.utc)

    try:
        db_data.urls.insert_one(
            {
                "short_code": short_code,
                "original_url": original_url,
                "created_at": created_at,
            }
        )
        db_data.url_stats.insert_one({"short_code": short_code, "visit_count": 0})
    except PyMongoError:
        print("⚠️ DB disconnected during insert. API offline mode.")

    return {
        "success": True,
        "input_url": original_url,
        "short_code": short_code,
        "created_on": created_at,
    }


# API v1 – Version


@app.get("/version", response_model=VersionResponse)
def api_version():
    return VersionResponse(version=__version__)


# ----------------------------------------
# Register API router FIRST
# ----------------------------------------


@app.get("/{short_code}", tags=["Redirect"])
def redirect_to_original(short_code: str):
    if not SHORT_CODE_PATTERN.match(short_code):
        raise HTTPException(status_code=404)

    try:
        if db_data.urls is None or db_data.url_stats is None:
            db_data.connect_db()
    except Exception:
        pass

    if db_data.urls is None:
        raise HTTPException(
            status_code=404, detail="Short code not available (offline mode)"
        )

    try:
        record = db_data.urls.find_one({"short_code": short_code})
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Database disconnected")

    if not record:
        raise HTTPException(status_code=404, detail="Short code not found")

    try:
        db_data.url_stats.update_one(
            {"short_code": short_code}, {"$inc": {"visit_count": 1}}, upsert=True
        )
    except PyMongoError:
        pass

    return RedirectResponse(url=record["original_url"])


@api_v1.get("/help", tags=["Help"])
def get_help():
    return JSONResponse(
        status_code=200,
        content={
            "message": "Welcome to the Tiny URL Shortener API! Visit /docs for API documentation."
        },
    )


# Register router
# -------------------------------------------------
app.include_router(api_v1)
