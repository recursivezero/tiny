from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.db.data import urls as urls_collection
from app.utils.helper import generate_code, is_valid_url, sanitize_url
from app import __version__


app = FastAPI(
    title="Tiny API",
    version=__version__,
    description="Tiny URL Shortener API built with FastAPI",
)




class ShortenRequest(BaseModel):
    url: str = Field(..., example="https://example.com")


class ShortenResponse(BaseModel):
    input_url: str
    output_url: str
    created_on: datetime


class VersionResponse(BaseModel):
    version: str


@app.post(
    "/api/shorten",
    response_model=ShortenResponse,
    status_code=201,
    summary="Shorten a URL",
    description="Generate a short URL for a given long URL",
    tags=["URL"],
)
def shorten_url(payload: ShortenRequest):
    original_url = sanitize_url(payload.url)

    if not is_valid_url(original_url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    short_code = generate_code()
    while urls_collection.find_one({"short_code": short_code}):
        short_code = generate_code()

    created_at = datetime.now(timezone.utc)

    urls_collection.insert_one(
        {
            "short_code": short_code,
            "original_url": original_url,
            "created_at": created_at,
            "visit_count": 0,
        }
    )

    return ShortenResponse(
        input_url=original_url,
        output_url=f"http://127.0.0.1:8001/{short_code}",
        created_on=created_at,
    )


@app.get(
    "/api/version",
    response_model=VersionResponse,
    summary="API version",
    tags=["Meta"],
)
def version():
    return VersionResponse(version=__version__)
