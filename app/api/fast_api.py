import os
import re
import traceback
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pymongo.errors import PyMongoError
else:
    try:
        from pymongo.errors import PyMongoError
    except ImportError:

        class PyMongoError(Exception):
            pass


from app import __version__
from app.utils import db
from app.utils.cache import get_short_from_cache, set_cache_pair
from app.utils.helper import generate_code, is_valid_url, sanitize_url

SHORT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{6}$")
MAX_URL_LENGTH = 2048

app = FastAPI(
    title="Tiny API",
    version=__version__,
    description="Tiny URL Shortener API built with FastAPI",
)

api_v1 = APIRouter(prefix=os.getenv("API_VERSION", "/api/v1"), tags=["v1"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "INTERNAL_SERVER_ERROR"},
    )


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


@api_v1.post("/shorten", response_model=ShortenResponse, status_code=201)
def shorten_url(payload: ShortenRequest):
    print(" SHORTEN ENDPOINT HIT ", payload.url)
    raw_url = payload.url.strip()

    if len(raw_url) > MAX_URL_LENGTH:
        return JSONResponse(
            status_code=413, content={"success": False, "input_url": payload.url}
        )

    original_url = sanitize_url(raw_url)

    if not is_valid_url(original_url):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "INVALID_URL",
                "input_url": payload.url,
                "message": "Invalid URL",
            },
        )

    if db.collection is None:
        cached_short = get_short_from_cache(original_url)
        short_code = cached_short or generate_code()
        set_cache_pair(short_code, original_url)
        return {
            "success": True,
            "input_url": original_url,
            "short_code": short_code,
            "created_on": datetime.now(timezone.utc),
        }

    try:
        existing = db.collection.find_one({"original_url": original_url})
    except PyMongoError:
        existing = None

    if existing:
        return {
            "success": True,
            "input_url": original_url,
            "short_code": existing["short_code"],
            "created_on": existing["created_at"],
        }

    short_code = generate_code()
    try:
        db.collection.insert_one(
            {
                "short_code": short_code,
                "original_url": original_url,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except PyMongoError:
        pass

    return {
        "success": True,
        "input_url": original_url,
        "short_code": short_code,
        "created_on": datetime.now(timezone.utc),
    }


@app.get("/version")
def api_version():
    return {"version": __version__}


@api_v1.get("/help")
def get_help():
    return {"message": "Welcome to Tiny API. Visit /docs for API documentation."}


app.include_router(api_v1)
